import datetime
import time
from abc import ABCMeta, abstractmethod
from logging import info

import pandas
import peewee

import sliver.database as db
from sliver.exceptions import DisablingError, PostponingError
from sliver.price import Price
from sliver.strategies.status import StrategyStatus
from sliver.utils import get_timeframe_delta


def table_function(cls):
    return "exchange"


class Exchange(db.BaseModel):
    __metaclass__ = ABCMeta

    name = peewee.TextField(unique=True)
    rate_limit = peewee.IntegerField(default=1200)
    precision_mode = peewee.IntegerField(default=2)
    padding_mode = peewee.IntegerField(default=5)
    timeframes = peewee.TextField(null=True)
    type = peewee.IntegerField(default=0)
    api_endpoint = peewee.TextField(null=True)
    api_sandbox_endpoint = peewee.TextField(null=True)

    class Meta:
        table_function = table_function

    @property
    def api(self):
        return self._api

    @api.setter
    @abstractmethod
    def api(self, credential=None):
        ...

    @abstractmethod
    def api_call(call):
        ...

    @api_call
    @abstractmethod
    def api_fetch_time(self):
        ...

    @api_call
    @abstractmethod
    def api_fetch_balance(self):
        ...

    @api_call
    @abstractmethod
    def api_fetch_ticker(self, symbol):
        # returns None if unsupported
        ...

    @api_call
    @abstractmethod
    def api_fetch_last_price(self, symbol):
        ...

    @api_call
    @abstractmethod
    def api_fetch_ohlcv(
        self, symbol, timeframe, since=None, limit=None, page_size=None
    ):
        # returns pandas dataframe
        ...

    @api_call
    @abstractmethod
    def api_fetch_orders(self, symbol, oid=None, status=None):
        # single, all, or based on status (open, closed, canceled)
        ...

    @api_call
    @abstractmethod
    def api_cancel_orders(self, symbol, oid=None):
        # if oid is none, cancel all orders
        ...

    @api_call
    @abstractmethod
    def api_create_order(self, symbol, type, side, amount, price):
        # returns oid if order was created, None otherwise
        ...

    @api_call
    @abstractmethod
    def get_synced_order(self, position, oid):
        ...

    @abstractmethod
    def sync_user_balance(self, user):
        ...

    def check_latency(self):
        started = time.perf_counter()
        self.api_fetch_time()
        elapsed = time.perf_counter() - started
        elapsed_in_ms = int(elapsed * 1000)
        if elapsed_in_ms > 5000:
            raise PostponingError(f"latency above threshold: {elapsed_in_ms} > 5000")

    def fetch_ohlcv(self, market, timeframe):
        info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        info(
            f"fetching ohlcv data for {market.get_symbol()} {timeframe} in {self.name}"
        )

        tf_delta = get_timeframe_delta(timeframe)

        if self.api_fetch_ticker(market.get_symbol()) is None:
            raise DisablingError("symbol not supported by exchange")

        # check if timeframe is supported by exchange
        # if timeframe not in api.timeframes:
        #     raise BaseError("timeframe not supported")

        try:
            last_entry = (
                Price.get_by_market(market, timeframe)
                .order_by(Price.time.desc())
                .get()
                .time
            )
            page_start = last_entry + tf_delta
            fetch_all = False

        except Price.DoesNotExist:
            page_start = None
            fetch_all = True

        prices = pandas.DataFrame(
            columns=["time", "open", "high", "low", "close", "volume"]
        )

        default_page_size = None

        while True:
            page = self.api_fetch_ohlcv(
                market.get_symbol(),
                timeframe,
                since=page_start,
                limit=default_page_size,
            )

            page_size = len(page)
            if default_page_size is None and page_size > 0:
                default_page_size = page_size
                last_candle = page.iloc[-1]
                if datetime.datetime.utcnow() <= last_candle.time + tf_delta:
                    page = page[:-1].copy()  # last candle is incomplete

            if page.empty:
                info("price data is up to date")
                break

            page_first = page.iloc[0].time
            page_last = page.iloc[-1].time
            info(f"received prices from {page_first} to {page_last}")
            prices = pandas.concat([prices, page])

            if (
                (page_start is not None and page_start != page_first)
                or (not fetch_all and page_start == page_first)
                or page_size != default_page_size
            ):
                info("price data is up to date")
                break

            page_start = page_first - page_size * tf_delta

        prices = prices.sort_values(by="time")
        prices = prices.drop_duplicates()

        prices["timeframe"] = timeframe
        prices["market_id"] = market.id

        prices[["open", "high", "low", "close"]] = prices[
            ["open", "high", "low", "close"]
        ].applymap(market.quote.transform)

        prices["volume"] = prices["volume"].apply(market.base.transform)

        with db.connection.atomic():
            if not prices.empty:
                Price.insert_many(prices.to_dict("records")).execute()

            from sliver.strategy import BaseStrategy

            for base_st in BaseStrategy.get_fetching(market, timeframe):
                base_st.status = StrategyStatus.WAITING
                base_st.save()

        return prices

    def create_order(self, position, type, side, amount, price):
        market = position.user_strategy.strategy.market

        info(
            f"inserting {type} {side} order "
            f":: {market.base.print(amount)} @ {market.quote.print(price)}"
        )

        if not market.is_valid_amount(amount, price):
            info("order values are smaller than minimum")
            return False

        amount = market.base.format(amount)
        price = market.quote.format(price)

        oid = self.api_create_order(market.get_symbol(), type, side, amount, price)
        if oid:
            info(f"inserted {type} {side} order {oid}")

            order = self.get_synced_order(position, oid)

            if order.status != "open":
                position.add_order(order)

            return order.exchange_order_id

    def create_limit_buy_orders(
        self, position, total_cost, last_price, num_orders, spread_pct
    ):
        market = position.user_strategy.strategy.market

        # compute price delta based on given spread
        delta = market.quote.div(
            last_price * spread_pct,
            market.quote.transform(100),
            prec=market.price_precision,
        )

        init_price = last_price - delta

        # compute cost for each order given a number of orders to create
        unit_cost = market.quote.div(
            total_cost,
            market.quote.transform(num_orders),
            prec=market.price_precision,
        )

        # compute prices for each order
        unit_spread = market.quote.div(
            delta,
            market.quote.transform(num_orders),
            prec=market.price_precision,
        )
        spreads = [init_price] + [unit_spread] * num_orders
        prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

        info(f"unit cost is {market.quote.print(unit_cost)}")

        # send a single order if cost of each order is lower than market min.
        if unit_cost < market.cost_min:
            info("unitary cost is less than exchange minimum, creating single order")

            # get average price for single order
            avg_price = market.quote.div(
                sum(prices),
                market.quote.transform(len(prices)),
                prec=market.price_precision,
            )
            total_amt = market.base.div(
                total_cost, avg_price, prec=market.amount_precision
            )

            self.create_order(position, "limit", "buy", total_amt, avg_price)

            return True

        # avoid rounding errors
        cost_remainder = total_cost - sum([unit_cost] * num_orders)
        if cost_remainder != 0:
            info(f"bucket remainder: {market.quote.print(cost_remainder)}")

        # creates bucket orders if reached here, which normally it will
        for price in prices:
            unit_amount = market.base.div(
                unit_cost, price, prec=market.amount_precision
            )

            if price == prices[-1]:
                unit_amount += market.base.div(
                    cost_remainder, price, prec=market.amount_precision
                )

            self.create_order(position, "limit", "buy", unit_amount, price)

        return True

    def create_limit_sell_orders(
        self, position, total_amount, last_price, num_orders, spread_pct
    ):
        market = position.user_strategy.strategy.market

        # compute price delta based on given spread
        delta = market.quote.div(
            last_price * spread_pct,
            market.quote.transform(100),
            prec=market.price_precision,
        )
        init_price = last_price + delta

        # compute prices for each order
        unit_spread = market.quote.div(
            -delta,
            market.quote.transform(num_orders),
            prec=market.price_precision,
        )
        spreads = [init_price] + [unit_spread] * num_orders
        prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

        # compute amount for each order given a number of orders to create
        unit_amount = market.base.div(
            total_amount,
            market.base.transform(num_orders),
            prec=market.amount_precision,
        )

        # compute costs
        amount_in_decimal = market.base.format(unit_amount)
        costs = [int(amount_in_decimal * p) for p in prices]

        # get average price for single order
        avg_price = market.quote.div(
            sum(prices),
            market.quote.transform(len(prices)),
            prec=market.price_precision,
        )

        info(f"unit amount is {market.base.print(unit_amount)}")

        # send a single order if any of the costs is lower than market minimum
        if any(cost < market.cost_min for cost in costs):
            info("unitary cost is less than exchange minimum, creating single order")
            self.create_order(position, "limit", "sell", total_amount, avg_price)
            return True

        # avoid bucket rounding errors
        bucket_remainder = total_amount - sum([unit_amount] * num_orders)
        if bucket_remainder != 0:
            info(f"bucket remainder {market.base.print(bucket_remainder)}")

        # creates bucket orders if reached here, which normally it will
        for price in prices:
            if price == prices[-1]:
                unit_amount += bucket_remainder

            self.create_order(position, "limit", "sell", unit_amount, price)

        return True
