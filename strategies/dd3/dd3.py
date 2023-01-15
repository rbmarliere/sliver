import pandas
import peewee

import core
from ..base import BaseStrategy


class DD3Indicator(core.db.BaseModel):
    indicator = peewee.ForeignKeyField(core.db.Indicator,
                                       primary_key=True,
                                       on_delete="CASCADE")
    ma1 = peewee.BigIntegerField()
    ma2 = peewee.BigIntegerField()
    ma3 = peewee.BigIntegerField()


class DD3Strategy(BaseStrategy):
    ma1_period = peewee.IntegerField(default=3)
    ma2_period = peewee.IntegerField(default=8)
    ma3_period = peewee.IntegerField(default=20)

    def get_indicators(self):
        return super() \
            .get_indicators() \
            .select(core.db.Price, core.db.Indicator, DD3Indicator) \
            .join(DD3Indicator, peewee.JOIN.LEFT_OUTER)

    def get_indicators_df(self):
        df = super().get_indicators_df(self.get_indicators())
        df.ma1 = df.ma1.apply(self.qformat)
        df.ma2 = df.ma2.apply(self.qformat)
        df.ma3 = df.ma3.apply(self.qformat)
        return df

    def refresh(self):
        self.refresh_indicators()

    def refresh_indicators(self):
        indicators = pandas.DataFrame(self.get_indicators().dicts())

        indicators.ma1 = indicators.close.rolling(self.ma1_period).mean()
        indicators.ma1.fillna(method="bfill", inplace=True)
        indicators.ma2 = indicators.close.rolling(self.ma2_period).mean()
        indicators.ma2.fillna(method="bfill", inplace=True)
        indicators.ma3 = indicators.close.rolling(self.ma3_period).mean()
        indicators.ma3.fillna(method="bfill", inplace=True)

        buy_rule = (
            (indicators.ma3 > indicators.ma2) &
            (indicators.ma2 > indicators.ma1) &
            (indicators.ma3 < indicators.close) &
            (indicators.ma1 > indicators.open))
        sell_rule = (
            (indicators.ma3 < indicators.ma2) &
            (indicators.ma2 < indicators.ma1) &
            (indicators.ma3 > indicators.close) &
            (indicators.ma1 < indicators.open))

        indicators.signal = "neutral"
        indicators.loc[buy_rule, "signal"] = "buy"
        indicators.loc[sell_rule, "signal"] = "sell"

        indicators.strategy = self.strategy.id
        indicators.price = indicators.id

        # insert only new indicators
        indicators = indicators.loc[indicators.indicator.isnull()]
        if indicators.empty:
            return

        with core.db.connection.atomic():
            core.db.Indicator.insert_many(
                indicators[["strategy", "price", "signal"]]
                .to_dict("records")
            ).execute()

            first = indicators[["strategy", "price", "signal"]].iloc[0]
            first_id = core.db.Indicator.get(**first.to_dict()).id
            indicators.indicator = range(first_id, first_id + len(indicators))

            DD3Indicator.insert_many(
                indicators[["indicator", "ma1", "ma2", "ma3"]]
                .to_dict("records")
            ).execute()
