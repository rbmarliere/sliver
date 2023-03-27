import random

import pandas

from sliver.indicator import Indicator
from sliver.print import print
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy


class RandomStrategy(IStrategy):
    def refresh_indicators(self):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        indicators = pandas.DataFrame(self.get_indicators().dicts())

        # remove non-empty rows
        indicators = indicators[indicators.isnull().any(axis=1)]
        if indicators.empty:
            print("indicator data is up to date")
            return

        indicators["strategy"] = self.strategy.id

        indicators = indicators.rename(
            columns={"id": "price_id", "strategy": "strategy_id"}
        )

        indicators.signal = indicators.signal.apply(
            lambda x: random.choice([BUY, NEUTRAL, SELL])
        )

        indicators = indicators[["price_id", "strategy_id", "signal"]]

        Indicator.insert_many(indicators.to_dict("records")).execute()
