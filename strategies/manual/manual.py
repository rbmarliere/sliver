import peewee

from ..base import BaseStrategy


class ManualStrategy(BaseStrategy):
    signal = peewee.TextField(null=True)

    def refresh(self, signal=None):
        if signal:
            self.signal = signal
            self.save()

    def get_signal(self):
        return self.signal
