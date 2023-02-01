import pandas
import peewee

import core
from ..base import BaseStrategy


class BBIndicator(core.db.BaseModel):
    indicator = peewee.ForeignKeyField(core.db.Indicator,
                                       primary_key=True,
                                       on_delete="CASCADE")
    ma = peewee.BigIntegerField(null=True)
    bolu = peewee.BigIntegerField(null=True)
    bold = peewee.BigIntegerField(null=True)
    tp = peewee.BigIntegerField(null=True)


class BBStrategy(BaseStrategy):
    use_ema = peewee.BooleanField(default=False)
    ma_period = peewee.IntegerField(default=20)
    num_std = peewee.IntegerField(default=2)

    def get_indicators(self):
        return super() \
            .get_indicators() \
            .select(*[*self.select_fields, BBIndicator]) \
            .join(BBIndicator, peewee.JOIN.LEFT_OUTER)

    def get_indicators_df(self):
        df = super().get_indicators_df(self.get_indicators())
        df.ma = df.ma * df.qprec
        df.ma = df.ma.astype(float).round(self.price_precision)
        df.bolu = df.bolu * df.qprec
        df.bolu = df.bolu.astype(float).round(self.price_precision)
        df.bold = df.bold * df.qprec
        df.bold = df.bold.astype(float).round(self.price_precision)
        return df

    def refresh(self):
        self.refresh_indicators()

    def refresh_indicators(self):
        BUY = core.strategies.Signal.BUY.value
        NEUTRAL = core.strategies.Signal.NEUTRAL.value
        SELL = core.strategies.Signal.SELL.value

        indicators = pandas.DataFrame(self.get_indicators().dicts())

        indicators.tp = \
            (indicators.high + indicators.low + indicators.close) / 3
        indicators.ma = indicators.tp.rolling(self.ma_period).mean()
        std = indicators.tp.rolling(self.ma_period).std(ddof=0)
        indicators.bolu = indicators.ma + self.num_std * std
        indicators.bold = indicators.ma - self.num_std * std

        buy_rule = indicators.close < indicators.bold
        sell_rule = indicators.close > indicators.bolu

        indicators.signal = NEUTRAL
        indicators.loc[buy_rule, "signal"] = BUY
        indicators.loc[sell_rule, "signal"] = SELL

        indicators = indicators.loc[indicators.indicator.isnull()]
        if indicators.empty:
            return

        indicators.fillna(method="bfill", inplace=True)

        with core.db.connection.atomic():
            indicators.strategy = self.strategy.id
            indicators.price = indicators.id

            core.db.Indicator.insert_many(
                indicators[["strategy", "price", "signal"]]
                .to_dict("records")
            ).execute()

            first = indicators[["strategy", "price", "signal"]].iloc[0]
            first_id = core.db.Indicator.get(**first.to_dict()).id
            indicators.indicator = range(first_id, first_id + len(indicators))

            BBIndicator.insert_many(
                indicators[["indicator", "ma", "bolu", "bold", "tp"]]
                .to_dict("records")
            ).execute()
