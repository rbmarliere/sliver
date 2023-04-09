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

    def get_indicators(self):
        return self.strategy.get_indicators(model=BBIndicator)

    def get_indicators_df(self):
        df = self.strategy.get_indicators_df(self.get_indicators())

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

        indicators = pandas.DataFrame(self.get_indicators().dicts())
        indicators["strategy"] = self.strategy.id
        indicators["price"] = indicators.id

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

        indicators = indicators.loc[indicators.indicator_id.isnull()].copy()
        if indicators.empty:
            return

        Indicator.insert_many(
            indicators[["strategy", "price", "signal"]].to_dict("records")
        ).execute()

        first = indicators[["strategy", "price", "signal"]].iloc[0]
        first_id = Indicator.get(**first.to_dict()).id
        indicators.indicator = range(first_id, first_id + len(indicators))

        BBIndicator.insert_many(
            indicators[["indicator", "ma", "bolu", "bold", "tp"]].to_dict("records")
        ).execute()
