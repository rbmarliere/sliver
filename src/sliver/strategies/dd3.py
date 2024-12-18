import decimal

import peewee

import sliver.database as db
from sliver.indicator import Indicator
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import quantize


class DD3Indicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    ma1 = peewee.BigIntegerField()
    ma2 = peewee.BigIntegerField()
    ma3 = peewee.BigIntegerField()


class DD3Strategy(IStrategy):
    ma1_period = peewee.IntegerField(default=3)
    ma2_period = peewee.IntegerField(default=8)
    ma3_period = peewee.IntegerField(default=20)

    @staticmethod
    def get_indicator_class():
        return DD3Indicator

    @staticmethod
    def setup():
        db.connection.create_tables([DD3Strategy, DD3Indicator])

    def get_indicators_df(self, **kwargs):
        df = super().get_indicators_df(**kwargs)

        if df.empty:
            return df

        df.ma1 = df.ma1.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma2 = df.ma2.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma3 = df.ma3.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma1 = df.ma1 * df.quote_precision
        df.ma2 = df.ma2 * df.quote_precision
        df.ma3 = df.ma3 * df.quote_precision
        df.ma1 = df.apply(lambda x: quantize(x, "ma1", "price_precision"), axis=1)
        df.ma2 = df.apply(lambda x: quantize(x, "ma2", "price_precision"), axis=1)
        df.ma3 = df.apply(lambda x: quantize(x, "ma3", "price_precision"), axis=1)

        return df

    def refresh_indicators(self, indicators, pending, reset=False):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        indicators.ma1 = indicators.close.rolling(self.ma1_period).mean()
        indicators.ma1.fillna(method="bfill", inplace=True)
        indicators.ma2 = indicators.close.rolling(self.ma2_period).mean()
        indicators.ma2.fillna(method="bfill", inplace=True)
        indicators.ma3 = indicators.close.rolling(self.ma3_period).mean()
        indicators.ma3.fillna(method="bfill", inplace=True)

        buy_rule = (
            (indicators.ma3 > indicators.ma2)
            & (indicators.ma2 > indicators.ma1)
            & (indicators.ma3 < indicators.close)
            & (indicators.ma1 > indicators.open)
        )
        sell_rule = (
            (indicators.ma3 < indicators.ma2)
            & (indicators.ma2 < indicators.ma1)
            & (indicators.ma3 > indicators.close)
            & (indicators.ma1 < indicators.open)
        )

        indicators.signal = NEUTRAL
        indicators.loc[buy_rule, "signal"] = BUY
        indicators.loc[sell_rule, "signal"] = SELL

        return indicators
