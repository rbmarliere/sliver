import pandas
import peewee

import core
from ..base import BaseStrategy


class SwapperBoxStrategy(BaseStrategy):
    url = peewee.TextField(null=True)
    telegram = peewee.TextField(null=True)

    def refresh(self):
        self.refresh_indicators()

    def refresh_indicators(self):
        BUY = core.strategies.Signal.BUY.value
        NEUTRAL = core.strategies.Signal.NEUTRAL.value
        SELL = core.strategies.Signal.SELL.value

        indicators = pandas.DataFrame(self.get_indicators().dicts())
        indicators = indicators.set_index("time")
        existing = indicators.dropna()

        if existing.empty:
            # signals = pandas.read_html(self.url)[1]
            si = pandas.read_csv("strategies/swapperbox/signals.tsv", sep="\t")
            si.time = pandas.to_datetime(si.time)
            freq = core.utils.get_timeframe_freq(self.strategy.timeframe)
            si = si.set_index("time").resample(freq).bfill()

            indicators.signal = NEUTRAL
            indicators.loc[si.signal == BUY, "signal"] = BUY
            indicators.loc[si.signal == SELL, "signal"] = SELL

            with core.db.connection.atomic():
                indicators["strategy"] = self.strategy.id
                indicators["price"] = indicators.id

                core.db.Indicator.insert_many(
                    indicators[["strategy", "price", "signal"]]
                    .to_dict("records")
                ).execute()
