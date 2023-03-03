from decimal import Decimal as D

import numpy
import pandas
import peewee

import core


class BaseStrategy(core.db.BaseModel):
    strategy = peewee.ForeignKeyField(core.db.Strategy, primary_key=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__.update(self.strategy.__data__)

        def p(p):
            return D("10") ** (D("-1") * p)

        self.amount_precision = D(self.strategy.market.amount_precision)
        self.base_precision = p(self.strategy.market.base.precision)
        self.price_precision = D(self.strategy.market.price_precision)
        self.quote_precision = p(self.strategy.market.quote.precision)

        self.select_fields = [
            core.db.Price,
            core.db.Indicator,
        ]

    def get_signal(self):
        try:
            signal = self.strategy \
                .indicator_set \
                .where(core.db.Indicator.signal
                       != core.strategies.Signal.NEUTRAL.value) \
                .order_by(core.db.Indicator.id.desc()) \
                .get().signal
            return core.strategies.Signal(signal)
        except core.db.Indicator.DoesNotExist:
            return core.strategies.Signal.NEUTRAL

    def get_indicators(self):
        return self.strategy.get_prices() \
            .select(*self.select_fields) \
            .join(core.db.Indicator,
                  peewee.JOIN.LEFT_OUTER,
                  on=((core.db.Indicator.price_id == core.db.Price.id)
                      & (core.db.Indicator.strategy == self)))

    def get_indicators_df(self, query=None):
        BUY = core.strategies.Signal.BUY.value
        SELL = core.strategies.Signal.SELL.value

        if query is None:
            query = self.get_indicators()

        df = pandas.DataFrame(query.dicts())

        if df.empty:
            return df

        df["amount_precision"] = self.amount_precision
        df["base_precision"] = self.base_precision
        df["price_precision"] = self.price_precision
        df["quote_precision"] = self.quote_precision

        df.open = df.open * df.quote_precision
        df.high = df.high * df.quote_precision
        df.low = df.low * df.quote_precision
        df.close = df.close * df.quote_precision
        df.volume = df.volume * df.base_precision

        df["buys"] = numpy.where(
            df.signal == BUY, df.close * D("0.995"), D(0))
        df.buys = df.apply(
            lambda x: core.utils.quantize(x, "buys", "price_precision"),
            axis=1)
        df.buys.replace({0: None}, inplace=True)

        df["sells"] = numpy.where(
            df.signal == SELL, df.close * D("1.005"), D(0))
        df.sells = df.apply(
            lambda x: core.utils.quantize(x, "sells", "price_precision"),
            axis=1)
        df.sells.replace({0: None}, inplace=True)

        df.open = df.apply(
            lambda x: core.utils.quantize(x, "open", "price_precision"),
            axis=1)

        df.high = df.apply(
            lambda x: core.utils.quantize(x, "high", "price_precision"),
            axis=1)

        df.low = df.apply(
            lambda x: core.utils.quantize(x, "low", "price_precision"),
            axis=1)

        df.close = df.apply(
            lambda x: core.utils.quantize(x, "close", "price_precision"),
            axis=1)

        df.volume = df.apply(
            lambda x: core.utils.quantize(x, "volume", "amount_precision"),
            axis=1)

        return df

    def refresh(self):
        pass

    def refresh_indicators(self):
        pass

    def load_fields(self, user):
        self.id = self.strategy_id
        self.market_id = self.strategy.market_id
        self.buy_engine_id = self.strategy.buy_engine_id
        self.sell_engine_id = self.strategy.sell_engine_id
        self.stop_engine_id = self.strategy.stop_engine_id
        self.subscribed = user.is_subscribed(self.id)
        self.signal = self.get_signal().value
        self.symbol = self.strategy.market.get_symbol()
        self.exchange = self.strategy.market.quote.exchange.name
