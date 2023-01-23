import peewee

import core
from ..base import BaseStrategy


class ManualStrategy(BaseStrategy):
    signal = peewee.DecimalField(default=0)

    def refresh(self, signal=None):
        if signal:
            self.signal = signal
            self.save()

    def get_signal(self):
        return core.strategies.Signal(self.signal)
