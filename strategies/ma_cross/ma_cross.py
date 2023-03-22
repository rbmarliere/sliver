import decimal

import pandas
import peewee

import core
from ..base import BaseStrategy


class MACrossIndicator(core.db.BaseModel):
    indicator = peewee.ForeignKeyField(
        core.db.Indicator, primary_key=True, on_delete="CASCADE"
    )
    fast = peewee.BigIntegerField()
    slow = peewee.BigIntegerField()


class MACrossStrategy(BaseStrategy):
    use_fast_ema = peewee.BooleanField(default=False)
    fast_period = peewee.IntegerField(default=50)
    use_slow_ema = peewee.BooleanField(default=False)
    slow_period = peewee.IntegerField(default=200)

    def get_indicators(self):
        return (
            super()
            .get_indicators()
            .select(*[*self.select_fields, MACrossIndicator])
            .join(MACrossIndicator, peewee.JOIN.LEFT_OUTER)
        )

    def get_indicators_df(self):
        df = super().get_indicators_df(self.get_indicators())

        df.fast = df.fast.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.slow = df.slow.apply(lambda x: decimal.Decimal(x) if x else 0)

        df.fast = df.fast * df.quote_precision
        df.slow = df.slow * df.quote_precision

        df.replace({float("nan"): None}, inplace=True)

        df.fast = df.apply(
            lambda x: core.utils.quantize(x, "fast", "price_precision"), axis=1
        )

        df.slow = df.apply(
            lambda x: core.utils.quantize(x, "slow", "price_precision"), axis=1
        )

        return df

    def refresh(self):
        self.refresh_indicators()

    def refresh_indicators(self):
        BUY = core.strategies.Signal.BUY
        NEUTRAL = core.strategies.Signal.NEUTRAL
        SELL = core.strategies.Signal.SELL

        indicators = pandas.DataFrame(self.get_indicators().dicts())

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

        # insert only new indicators
        indicators = indicators.loc[indicators.indicator.isnull()]
        if indicators.empty:
            return

        with core.db.connection.atomic():
            indicators["strategy"] = self.strategy.id
            indicators["price"] = indicators.id

            core.db.Indicator.insert_many(
                indicators[["strategy", "price", "signal"]].to_dict("records")
            ).execute()

            first = indicators[["strategy", "price", "signal"]].iloc[0]
            first_id = core.db.Indicator.get(**first.to_dict()).id
            indicators.indicator = range(first_id, first_id + len(indicators))

            MACrossIndicator.insert_many(
                indicators[["indicator", "fast", "slow"]].to_dict("records")
            ).execute()
