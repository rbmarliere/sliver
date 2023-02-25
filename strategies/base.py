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

        self.amount_precision = self.strategy.market.amount_precision
        self.base_precision = self.strategy.market.base.precision
        self.price_precision = self.strategy.market.price_precision
        self.quote_precision = self.strategy.market.quote.precision

        self.select_fields = [
            core.db.Price,
            core.db.Indicator,
            peewee.Value(10**(-1*self.base_precision)).alias("bprec"),
            peewee.Value(10**(-1*self.quote_precision)).alias("qprec"),
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

        df.open = df.open * df.qprec
        df.high = df.high * df.qprec
        df.low = df.low * df.qprec
        df.close = df.close * df.qprec
        df.volume = df.volume * df.bprec

        df["buys"] = numpy.where(
            df.signal == BUY, df.close * D("0.995"), numpy.nan)
        df.buys.replace({float("nan"): None}, inplace=True)

        df["sells"] = numpy.where(
            df.signal == SELL, df.close * D("1.005"), numpy.nan)
        df.sells.replace({float("nan"): None}, inplace=True)

        df.buys = df.buys.astype(float).round(self.price_precision)
        df.sells = df.sells.astype(float).round(self.price_precision)
        df.open = df.open.astype(float).round(self.price_precision)
        df.high = df.high.astype(float).round(self.price_precision)
        df.low = df.low.astype(float).round(self.price_precision)
        df.close = df.close.astype(float).round(self.price_precision)
        df.volume = df.volume.astype(float).round(self.amount_precision)

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
