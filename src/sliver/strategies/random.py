import random

import sliver.database as db
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy


class RandomStrategy(IStrategy):
    @staticmethod
    def setup():
        db.connection.create_tables([RandomStrategy])

    def refresh_indicators(self, indicators, pending, reset=False):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        pending.signal = pending.signal.apply(
            lambda x: random.choice([BUY, NEUTRAL, SELL])
        )

        return pending
