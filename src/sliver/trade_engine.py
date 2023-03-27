import peewee

import sliver.database as db


class TradeEngine(db.BaseModel):
    description = peewee.TextField()
    deleted = peewee.BooleanField(default=False)
    refresh_interval = peewee.IntegerField(default=1)
    num_orders = peewee.IntegerField(default=1)
    bucket_interval = peewee.IntegerField(default=60)
    min_buckets = peewee.IntegerField(default=1)
    spread = peewee.DecimalField(default=1)
    stop_cooldown = peewee.IntegerField(default=1440)
    stop_gain = peewee.DecimalField(default=5)
    trailing_gain = peewee.BooleanField(default=False)
    stop_loss = peewee.DecimalField(default=5)
    trailing_loss = peewee.BooleanField(default=False)
    lm_ratio = peewee.DecimalField(default=0)
