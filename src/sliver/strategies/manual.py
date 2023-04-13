import peewee

import sliver.database as db
from sliver.strategy import IStrategy


class ManualStrategy(IStrategy):
    signal = peewee.DecimalField(default=0)

    @staticmethod
    def setup():
        db.connection.create_tables([ManualStrategy])

    def get_signal(self):
        return self.signal

    def refresh_indicators(self, indicators, signal=None):
        if signal:
            self.signal = signal
            self.save()
