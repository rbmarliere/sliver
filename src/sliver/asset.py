import peewee

import sliver.database as db


class Asset(db.BaseModel):
    ticker = peewee.TextField(unique=True)
