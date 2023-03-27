import peewee

import sliver.database as db


class Order(db.BaseModel):
    position = peewee.DeferredForeignKey("Position", null=True)
    exchange_order_id = peewee.TextField()
    time = peewee.DateTimeField()
    status = peewee.TextField()
    type = peewee.TextField()
    side = peewee.TextField()
    price = peewee.BigIntegerField()
    amount = peewee.BigIntegerField()
    cost = peewee.BigIntegerField()
    filled = peewee.BigIntegerField()
    fee = peewee.BigIntegerField()
