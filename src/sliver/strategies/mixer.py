import datetime
from decimal import Decimal as D

import pandas
import peewee

import sliver.database as db
from sliver.exceptions import DisablingError
from sliver.indicator import Indicator
from sliver.strategies.signals import StrategySignals
from sliver.strategy import BaseStrategy, IStrategy
from sliver.utils import get_timeframe_freq


class MixerIndicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    buy_w_signal = peewee.DecimalField(default=0)
    sell_w_signal = peewee.DecimalField(default=0)


class MixedStrategies(db.BaseModel):
    mixer = peewee.ForeignKeyField(BaseStrategy, on_delete="CASCADE", backref="mixins")
    strategy = peewee.ForeignKeyField(BaseStrategy, on_delete="CASCADE")
    buy_weight = peewee.DecimalField(default=1)
    sell_weight = peewee.DecimalField(default=1)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (mixer_id, strategy_id)")]


class MixerStrategy(IStrategy):
    buy_threshold = peewee.DecimalField(default=1)
    sell_threshold = peewee.DecimalField(default=-1)

    @staticmethod
    def get_indicator_class():
        return MixerIndicator

    @staticmethod
    def setup():
        db.connection.create_tables([MixerStrategy, MixerIndicator, MixedStrategies])

    def refresh_indicators(self, indicators, pending, reset=False):
        from sliver.strategies.factory import StrategyFactory

        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        indicators = indicators.set_index("time")
        indicators.drop("signal", axis=1, inplace=True)
        indicators["buy_w_signal"] = D(NEUTRAL)
        indicators["sell_w_signal"] = D(NEUTRAL)

        for mixin in self.strategy.mixins:
            strategy = StrategyFactory.from_base(mixin.strategy)

            mixind = pandas.DataFrame(strategy.get_indicators().dicts())
            if mixind.empty:
                raise DisablingError("no mixin indicator data")

            mixind = mixind.set_index("time")

            if self.strategy.timeframe != strategy.timeframe:
                freq = get_timeframe_freq(self.strategy.timeframe)
                new_row = pandas.DataFrame(index=[datetime.datetime.utcnow()])
                mixind = pandas.concat([mixind, new_row])
                mixind = mixind.resample(freq).ffill()

            mixind["buy_weight"] = mixin.buy_weight
            mixind["buy_w_signal"] = mixind["signal"] * mixind["buy_weight"]
            indicators["buy_w_signal"] += mixind["buy_w_signal"]

            mixind["sell_weight"] = mixin.sell_weight
            mixind["sell_w_signal"] = mixind["signal"] * mixind["sell_weight"]
            indicators["sell_w_signal"] += mixind["sell_w_signal"]

        not_null = (indicators["buy_w_signal"].notna()) | (
            indicators["sell_w_signal"].notna()
        )
        indicators = indicators[not_null].copy()

        indicators.buy_w_signal.clip(lower=0, inplace=True)
        indicators.sell_w_signal.clip(upper=0, inplace=True)

        weighted_signal = indicators.buy_w_signal + indicators.sell_w_signal

        indicators["signal"] = weighted_signal.apply(
            lambda x: BUY
            if x >= self.buy_threshold
            else SELL
            if x <= self.sell_threshold
            else NEUTRAL
        )

        indicators = indicators.reset_index()

        return indicators

    def get_fields(self):
        from flask_restful import fields

        all_fields = super().get_fields()
        all_fields["mixins"] = fields.List(
            fields.Nested(
                {
                    "strategy_id": fields.Integer,
                    "buy_weight": fields.Float,
                    "sell_weight": fields.Float,
                }
            )
        )
        return all_fields
