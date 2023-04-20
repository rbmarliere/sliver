import peewee

import sliver.database as db
from sliver.exchange_asset import ExchangeAsset


class Balance(db.BaseModel):
    user = peewee.DeferredForeignKey("User", null=True)
    asset = peewee.ForeignKeyField(ExchangeAsset)
    total = peewee.BigIntegerField(null=True)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (asset_id, user_id)")]
