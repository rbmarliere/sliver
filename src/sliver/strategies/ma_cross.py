import decimal

import peewee

import sliver.database as db
from sliver.indicator import Indicator
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import quantize


class MACrossIndicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    fast = peewee.BigIntegerField()
    slow = peewee.BigIntegerField()


class MACrossStrategy(IStrategy):
    use_fast_ema = peewee.BooleanField(default=False)
    fast_period = peewee.IntegerField(default=50)
    use_slow_ema = peewee.BooleanField(default=False)
    slow_period = peewee.IntegerField(default=200)

    @staticmethod
    def get_indicator_class():
        return MACrossIndicator

    @staticmethod
    def setup():
        db.connection.create_tables([MACrossStrategy, MACrossIndicator])

    def get_indicators_df(self, **kwargs):
        df = super().get_indicators_df(**kwargs)

        if df.empty:
            return df

        df.fast = df.fast.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.slow = df.slow.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.fast = df.fast * df.quote_precision
        df.slow = df.slow * df.quote_precision
        df.fast = df.apply(lambda x: quantize(x, "fast", "price_precision"), axis=1)
        df.slow = df.apply(lambda x: quantize(x, "slow", "price_precision"), axis=1)

        return df

    def refresh_indicators(self, indicators):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        if self.use_fast_ema:
            indicators.fast = indicators.close.ewm(self.fast_period).mean()
        else:
            indicators.fast = indicators.close.rolling(self.fast_period).mean()

        if self.use_slow_ema:
            indicators.slow = indicators.close.ewm(self.slow_period).mean()
        else:
            indicators.slow = indicators.close.rolling(self.slow_period).mean()

        indicators.fast.fillna(method="bfill", inplace=True)
        indicators.slow.fillna(method="bfill", inplace=True)

        buy_rule = indicators.fast >= indicators.slow
        sell_rule = indicators.fast < indicators.slow

        indicators.signal = NEUTRAL
        indicators.loc[buy_rule, "signal"] = BUY
        indicators.loc[sell_rule, "signal"] = SELL

        return indicators
