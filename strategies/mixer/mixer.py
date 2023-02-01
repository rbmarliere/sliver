import pandas
import peewee

import core
from ..base import BaseStrategy


class MixerIndicator(core.db.BaseModel):
    indicator = peewee.ForeignKeyField(core.db.Indicator,
                                       primary_key=True,
                                       on_delete="CASCADE")
    weighted_signal = peewee.DecimalField(default=0)


class MixerStrategy(BaseStrategy):
    buy_threshold = peewee.DecimalField(default=1)
    sell_threshold = peewee.DecimalField(default=-1)

    def get_indicators(self):
        return super() \
            .get_indicators() \
            .select(*[*self.select_fields, MixerIndicator]) \
            .join(MixerIndicator, peewee.JOIN.LEFT_OUTER)

    def get_indicators_df(self):
        return super().get_indicators_df(self.get_indicators())

    def refresh(self):
        self.refresh_indicators()

    def refresh_indicators(self):
        BUY = core.strategies.Signal.BUY.value
        NEUTRAL = core.strategies.Signal.NEUTRAL.value
        SELL = core.strategies.Signal.SELL.value

        indicators = pandas.DataFrame(self.get_indicators().dicts())
        indicators.drop("signal", axis=1, inplace=True)
        indicators["weighted_signal"] = NEUTRAL

        # TODO buy_mixins vs sell_mixins
        # idea is to use different strategies for buy and sell signals
        for mixin in self.strategy.mixins:
            strategy = core.strategies.load(
                core.db.Strategy.get_by_id(mixin.strategy_id))
            mixind = pandas.DataFrame(strategy.get_indicators().dicts())
            mixind["weight"] = mixin.weight
            mixind["weighted_signal"] = mixind["signal"] * mixind["weight"]
            indicators["weighted_signal"] += mixind["weighted_signal"]

        indicators.weighted_signal = \
            indicators.weighted_signal.replace({float("nan"): 0})

        indicators["signal"] = indicators.weighted_signal.apply(
            lambda x: BUY if x >= self.buy_threshold else
            SELL if x <= self.sell_threshold else NEUTRAL)

        # insert only new indicators
        indicators = indicators.loc[indicators.indicator.isnull()]
        if indicators.empty:
            return

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

            MixerIndicator.insert_many(
                indicators[["indicator", "weighted_signal"]]
                .to_dict("records")
            ).execute()


class MixedStrategies(core.db.BaseModel):
    mixer = peewee.ForeignKeyField(core.db.Strategy,
                                   on_delete="CASCADE",
                                   backref="mixins")
    strategy = peewee.ForeignKeyField(core.db.Strategy,
                                      on_delete="CASCADE")
    weight = peewee.DecimalField(default=1)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (mixer_id, strategy_id)")]
