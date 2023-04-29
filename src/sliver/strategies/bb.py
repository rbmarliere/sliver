import decimal

import pandas
import peewee

import sliver.database as db
from sliver.indicator import Indicator
from sliver.indicators.bb import BB
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import quantize


class BBIndicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    ma = peewee.BigIntegerField(null=True)
    bolu = peewee.BigIntegerField(null=True)
    bold = peewee.BigIntegerField(null=True)
    tp = peewee.BigIntegerField(null=True)


class BBStrategy(IStrategy):
    use_ema = peewee.BooleanField(default=False)
    ma_period = peewee.IntegerField(default=20)
    num_std = peewee.IntegerField(default=2)

    @staticmethod
    def get_indicator_class():
        return BBIndicator

    @staticmethod
    def setup():
        db.connection.create_tables([BBStrategy, BBIndicator])

    def get_indicators_df(self, **kwargs):
        df = super().get_indicators_df(**kwargs)

        if df.empty:
            return df

        df.ma = df.ma.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.bolu = df.bolu.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.bold = df.bold.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma = df.ma * df.quote_precision
        df.bolu = df.bolu * df.quote_precision
        df.bold = df.bold * df.quote_precision
        df.ma = df.apply(lambda x: quantize(x, "ma", "price_precision"), axis=1)
        df.bolu = df.apply(lambda x: quantize(x, "bolu", "price_precision"), axis=1)
        df.bold = df.apply(lambda x: quantize(x, "bold", "price_precision"), axis=1)

        return df

    def refresh_indicators(self, indicators):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        indicators = BB(
            indicators,
            ma_period=self.ma_period,
            num_std=self.num_std,
            use_ema=self.use_ema,
        )

        buy_rule = indicators.close > indicators.bold
        sell_rule = indicators.close < indicators.bolu

        indicators.signal = NEUTRAL
        indicators.loc[buy_rule, "signal"] = BUY
        indicators.loc[sell_rule, "signal"] = SELL

        indicators.fillna(method="bfill", inplace=True)

        return indicators
