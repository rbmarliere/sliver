import datetime
from abc import ABC, abstractmethod

import pandas
import peewee

import core
from core.watchdog import info as i


class BaseExchange(ABC):
    credential = None
    exchange = None
    market = None
    position = None
    strategy = None

    def __init__(self,
                 exchange,
                 credential=None,
                 position=None,
                 strategy=None):
        if position:
            self.strategy = position.user_strategy.strategy
            self.market = position.user_strategy.strategy.market
            self.position = position

        if strategy:
            self.strategy = strategy
            self.market = strategy.market

        self.exchange = exchange
        self.credential = credential

        self.api = credential

    @property
    def api(self):
        return self._api

    @api.setter
    @abstractmethod
    def api(self, credential=None):
        ...

    @abstractmethod
    def api_fetch_time(self):
        ...

    @abstractmethod
    def api_fetch_balance(self):
        ...

    @abstractmethod
    def api_fetch_markets(self):
        ...

    @abstractmethod
    def api_fetch_ticker(self, symbol):
        # all price returns must be transformed?
        # ...only if self.position is not None
        # returns none if unsupported
        ...

    @abstractmethod
    def api_fetch_ohlcv(self,
                        symbol,
                        timeframe,
                        since=None,
                        limit=None,
                        page_size=None):
        # returns pandas dataframe
        ...

    @abstractmethod
    def api_fetch_orders(self, symbol, oid=None, status=None):
        # single, all, or based on status (open, closed, canceled)
        ...

    @abstractmethod
    def api_cancel_orders(self, symbol, oid=None):
        # if oid is none, cancel all orders
        ...

    @abstractmethod
    def api_create_order(self, type, side, amount, price=None):
        # returns oid if order was created, None otherwise
        ...

    def fetch_ohlcv(self):
        tf_delta = core.utils.get_timeframe_delta(self.strategy.timeframe)

        if self.api_fetch_ticker(self.market.get_symbol()) is None:
            raise core.errors.BaseError("symbol not supported by exchange")

        # check if timeframe is supported by exchange
        # if timeframe not in api.timeframes:
        #     raise core.errors.BaseError("timeframe not supported")

        try:
            filter = ((core.db.Price.market == self.market) &
                      (core.db.Price.timeframe == self.strategy.timeframe))
            desc = core.db.Price.time.desc()

            last_entry = core.db.Price \
                .select() \
                .where(filter) \
                .order_by(desc).get().time

            page_start = last_entry + tf_delta

        except peewee.DoesNotExist:
            last_entry = datetime.datetime.utcfromtimestamp(0)
            page_start = datetime.datetime(2000, 1, 1)
            i("no db entries found, downloading everything...")

        prices = pandas.DataFrame(columns=["time", "open", "high",
                                           "low", "close", "volume"])
        now = datetime.datetime.utcnow()

        while True:
            if (prices.empty and page_start + tf_delta > now) \
                    or page_start > now:
                i("price data is up to date")
                break

            i("downloading from {s}".format(s=page_start))
            page = self.api_fetch_ohlcv(self.market.get_symbol(),
                                        self.strategy.timeframe,
                                        since=page_start)

            prices = pandas.concat([prices, page])

            page_first = page.iloc[0].time
            page_last = page.iloc[-1].time
            i("received range {f} to {l}".format(f=page_first, l=page_last))

            page_start = page_last + tf_delta

        prices = prices[:-1].copy()  # last candle is incomplete
        prices["timeframe"] = self.strategy.timeframe
        prices["market_id"] = self.market.id

        prices[["open", "high", "low", "close"]] = \
            prices[["open", "high", "low", "close"]] \
            .applymap(self.market.quote.transform)

        prices["volume"] = prices["volume"] \
            .apply(self.market.base.transform)

        prices = prices.drop_duplicates()

        if not prices.empty:
            core.db.Price.insert_many(prices.to_dict("records")).execute()

        return prices

    def sync_limit_orders(self):
        # fetch internal open orders
        orders = self.position.get_open_orders()

        # if no orders found, exit
        if len(orders) == 0:
            i("no open orders found")
            return

        for order in orders:
            oid = order.exchange_order_id
            i("updating {s} order {i}".format(s=order.side, i=oid))

            ex_order = self.api_fetch_orders(self.market.get_symbol(),
                                             oid=oid)
            order.sync(ex_order, self.position)

    def create_order(self, type, side, amount, price):
        i("inserting {t} {s} order :: {a} @ {p}"
          .format(t=type,
                  s=side,
                  a=self.market.base.print(amount),
                  p=self.market.quote.print(price)))
        try:
            assert amount >= self.market.amount_min
            assert price >= self.market.price_min
            assert amount * price >= self.market.cost_min
        except AssertionError:
            i("order values are smaller than exchange minimum, skipping...")
            return

        amount = self.market.base.format(amount)
        price = self.market.quote.format(price)

        oid = self.api_create_order(type, side, amount, price)
        if oid:
            i("inserted {t} {s} order {i}".format(t=type, s=side, i=oid))

            ex_order = self.api_fetch_orders(self.market.get_symbol(),
                                             oid=oid)

            order = core.db.Order.sync(core.db.Order(),
                                       ex_order,
                                       self.position)
            return oid

    def create_limit_buy_orders(self,
                                total_cost,
                                last_price,
                                num_orders,
                                spread_pct):
        # compute price delta based on given spread
        delta = self.market.quote.div(last_price * spread_pct,
                                      self.market.quote.transform(100),
                                      prec=self.market.price_precision)

        init_price = last_price - delta

        # compute cost for each order given a number of orders to create
        unit_cost = self.market.quote.div(total_cost,
                                          self.market.quote.transform(
                                              num_orders),
                                          prec=self.market.price_precision)

        # compute prices for each order
        unit_spread = self.market.quote.div(delta,
                                            self.market.quote.transform(
                                                num_orders),
                                            prec=self.market.price_precision)
        spreads = [init_price] + [unit_spread] * num_orders
        prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

        i("unit cost is {c}".format(c=self.market.quote.print(unit_cost)))

        # send a single order if cost of each order is lower than market min.
        if unit_cost < self.market.cost_min:
            i("unitary cost is less than exchange minimum,"
              "creating single order")

            # get average price for single order
            avg_price = self.market.quote.div(sum(prices),
                                              self.market.quote.transform(
                                                  len(prices)),
                                              prec=self.market.price_precision)
            total_amt = self.market.base.div(total_cost,
                                             avg_price,
                                             prec=self.market.amount_precision)

            return self.create_order("limit",
                                     "buy",
                                     total_amt,
                                     avg_price)

        # avoid rounding errors
        cost_remainder = total_cost - sum([unit_cost] * num_orders)
        if cost_remainder != 0:
            i("bucket remainder: {r}".format(
                r=self.market.quote.print(cost_remainder)))

        # creates bucket orders if reached here, which normally it will
        for price in prices:
            amt = self.market.base.div(unit_cost,
                                       price,
                                       prec=self.market.amount_precision)

            if price == prices[-1]:
                amt += self.market.base.div(cost_remainder,
                                            price,
                                            prec=self.market.amount_precision)

            return self.create_order("limit",
                                     "buy",
                                     amt,
                                     price)

    def create_limit_sell_orders(self,
                                 total_amount,
                                 last_price,
                                 num_orders,
                                 spread_pct):
        # compute price delta based on given spread
        delta = self.market.quote.div(last_price * spread_pct,
                                      self.market.quote.transform(100),
                                      prec=self.market.price_precision)
        init_price = last_price + delta

        # compute prices for each order
        unit_spread = self.market.quote.div(-delta,
                                            self.market.quote.transform(
                                                num_orders),
                                            prec=self.market.price_precision)
        spreads = [init_price] + [unit_spread] * num_orders
        prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

        # compute amount for each order given a number of orders to create
        unit_amount = self.market.base.div(total_amount,
                                           self.market.base.transform(
                                               num_orders),
                                           prec=self.market.amount_precision)

        # compute costs
        amount_in_decimal = self.market.base.format(unit_amount)
        costs = [int(amount_in_decimal * p) for p in prices]

        # get average price for single order
        avg_price = self.market.quote.div(sum(prices),
                                          self.market.quote.transform(
                                              len(prices)),
                                          prec=self.market.price_precision)

        i("unit amount is {a}".format(a=self.market.base.print(unit_amount)))

        # send a single order if any of the costs is lower than market minimum
        if any(cost < self.market.cost_min for cost in costs):
            i("unitary cost is less than exchange minimum,"
              "creating single order")
            return self.create_order("limit",
                                     "sell",
                                     total_amount,
                                     avg_price)

        # avoid bucket rounding errors
        bucket_remainder = total_amount - sum([unit_amount] * num_orders)
        if bucket_remainder != 0:
            i("bucket remainder {r}".format(
                r=self.market.base.print(bucket_remainder)))

        # creates bucket orders if reached here, which normally it will
        for price in prices:
            if price == prices[-1]:
                unit_amount += bucket_remainder

            return self.create_order("limit",
                                     "sell",
                                     unit_amount,
                                     price)
