import peewee

import sliver.database as db
from sliver.price import Price


class Indicator(db.BaseModel):
    id = peewee.BigAutoField(primary_key=True)
    strategy = peewee.DeferredForeignKey("BaseStrategy", null=True)
    price = peewee.ForeignKeyField(Price)
    signal = peewee.DecimalField(default=0)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (price_id, strategy_id)")]
