import peewee

from sliver.strategy import IStrategy


class ManualStrategy(IStrategy):
    signal = peewee.DecimalField(default=0)

    def get_signal(self):
        return self.signal

    def refresh_indicators(self, indicators, signal=None):
        if signal:
            self.signal = signal
            self.save()
