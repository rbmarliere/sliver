import peewee

import core


class ManualStrategy(core.db.BaseModel):
    strategy = peewee.ForeignKeyField(core.db.Strategy)
    signal = peewee.TextField()

    def get_signal(self):
        return self.signal

    def set_signal(self, signal):
        self.signal = signal
        self.save()
