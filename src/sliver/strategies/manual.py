import peewee

from sliver.strategy import IStrategy


class ManualStrategy(IStrategy):
    signal = peewee.DecimalField(default=0)

    def refresh_indicators(self, signal=None):
        if signal:
            self.signal = signal
            self.save()
