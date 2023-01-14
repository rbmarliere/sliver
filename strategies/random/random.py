import random

import pandas

import core
from ..base import BaseStrategy


class RandomStrategy(BaseStrategy):
    def refresh(self):
        self.refresh_indicators()

    def refresh_indicators(self):
        indicators = pandas.DataFrame(self.get_indicators().dicts())

        # remove non-empty rows
        indicators = indicators[indicators.isnull().any(axis=1)]
        if indicators.empty:
            core.watchdog.info("indicator data is up to date")
            return

        indicators["strategy"] = self.strategy.id

        indicators = indicators.rename(columns={
            "id": "price_id",
            "strategy": "strategy_id"
        })

        indicators.signal = indicators.signal.apply(
            lambda x: random.choice(["buy", "sell", "neutral"]))

        indicators = indicators[["price_id", "strategy_id", "signal"]]

        core.db.Indicator.insert_many(indicators.to_dict("records")).execute()
