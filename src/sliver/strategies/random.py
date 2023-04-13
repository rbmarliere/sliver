import random

import sliver.database as db
from sliver.indicator import Indicator
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy


class RandomStrategy(IStrategy):
    @staticmethod
    def setup():
        db.connection.create_tables([RandomStrategy])

    def refresh_indicators(self, indicators):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        indicators.signal = indicators.signal.apply(
            lambda x: random.choice([BUY, NEUTRAL, SELL])
        )

        Indicator.insert_many(
            indicators[["strategy", "price", "signal"]].to_dict("records")
        ).execute()
