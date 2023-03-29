import datetime
from abc import ABCMeta, abstractmethod

import pandas
import peewee

import sliver.database as db
from sliver.exceptions import DisablingError, PostponingError
from sliver.price import Price
from sliver.print import print
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
    def api_fetch_markets(self):
        ...

    @api_call
    @abstractmethod
    def api_fetch_ticker(self, symbol):
        # returns None if unsupported
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
    def api_create_order(self, symbol, type, side, amount, price=None):
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
        started = datetime.datetime.utcnow()
        self.api_fetch_time()
        elapsed = datetime.datetime.utcnow() - started
        elapsed_in_ms = int(elapsed.total_seconds() * 1000)
        if elapsed_in_ms > 5000:
            msg = "latency above threshold: {l} > 5000".format(l=elapsed_in_ms)
            raise PostponingError(msg)

    def fetch_ohlcv(self, strategy):
        market = strategy.market
        tf_delta = get_timeframe_delta(strategy.timeframe)

        if self.api_fetch_ticker(market.get_symbol()) is None:
            raise DisablingError("symbol not supported by exchange")

        # check if timeframe is supported by exchange
        # if timeframe not in api.timeframes:
        #     raise BaseError("timeframe not supported")

        try:
            last_entry = (
                Price.get_by_strategy(strategy).order_by(Price.time.desc()).get().time
            )

            page_start = last_entry + tf_delta

        except Price.DoesNotExist:
            last_entry = datetime.datetime.utcfromtimestamp(0)
            page_start = datetime.datetime(2000, 1, 1)
            print("no db entries found, downloading everything")

        prices = pandas.DataFrame(
            columns=["time", "open", "high", "low", "close", "volume"]
        )
        now = datetime.datetime.utcnow()

        while True:
            if (prices.empty and page_start + tf_delta > now) or page_start > now:
                print("price data is up to date")
                break

            print("downloading from {s}".format(s=page_start))
            page = self.api_fetch_ohlcv(
                market.get_symbol(), strategy.timeframe, since=page_start
            )

            if page.empty:
                print("price data is up to date")
                break

            prices = pandas.concat([prices, page])

            page_first = page.iloc[0].time
            page_last = page.iloc[-1].time
            print("received range {f} - {l}".format(f=page_first, l=page_last))

            page_start = page_last + tf_delta

        prices = prices[:-1].copy()  # last candle is incomplete
        prices["timeframe"] = strategy.timeframe
        prices["market_id"] = market.id

        prices[["open", "high", "low", "close"]] = prices[
            ["open", "high", "low", "close"]
        ].applymap(market.quote.transform)

        prices["volume"] = prices["volume"].apply(market.base.transform)

        prices = prices.drop_duplicates()

        if not prices.empty:
            Price.insert_many(prices.to_dict("records")).execute()

        return prices

    def create_order(self, position, type, side, amount, price):
        market = position.user_strategy.strategy.market

        print(
            "inserting {t} {s} order :: {a} @ {p}".format(
                t=type,
                s=side,
                a=market.base.print(amount),
                p=market.quote.print(price),
            )
        )

        try:
            assert amount >= market.amount_min
            assert price >= market.price_min
            assert amount * price >= market.cost_min
        except AssertionError:
            print("order values are smaller than minimum")
            return False

        amount = market.base.format(amount)
        price = market.quote.format(price)

        oid = self.api_create_order(market.get_symbol(), type, side, amount, price)
        if oid:
            print("inserted {t} {s} order {i}".format(t=type, s=side, i=oid))

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

        print("unit cost is {c}".format(c=market.quote.print(unit_cost)))

        # send a single order if cost of each order is lower than market min.
        if unit_cost < market.cost_min:
            print("unitary cost is less than exchange minimum," "creating single order")

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
            print("bucket remainder: {r}".format(r=market.quote.print(cost_remainder)))

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

        print("unit amount is {a}".format(a=market.base.print(unit_amount)))

        # send a single order if any of the costs is lower than market minimum
        if any(cost < market.cost_min for cost in costs):
            print("unitary cost is less than exchange minimum," "creating single order")
            self.create_order(position, "limit", "sell", total_amount, avg_price)
            return True

        # avoid bucket rounding errors
        bucket_remainder = total_amount - sum([unit_amount] * num_orders)
        if bucket_remainder != 0:
            print("bucket remainder {r}".format(r=market.base.print(bucket_remainder)))

        # creates bucket orders if reached here, which normally it will
        for price in prices:
            if price == prices[-1]:
                unit_amount += bucket_remainder

            self.create_order(position, "limit", "sell", unit_amount, price)

        return True
