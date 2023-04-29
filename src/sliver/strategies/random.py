import random

import sliver.database as db
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy


class RandomStrategy(IStrategy):
    @staticmethod
    def setup():
        db.connection.create_tables([RandomStrategy])

    def refresh_indicators(self, indicators, pending):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        indicators.signal = indicators.signal.apply(
            lambda x: random.choice([BUY, NEUTRAL, SELL])
        )

        return indicators
