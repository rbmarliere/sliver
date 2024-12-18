from logging import info

import peewee

import sliver.database as db
from sliver.exchange import Exchange


class Credential(db.BaseModel):
    user = peewee.DeferredForeignKey("User", null=True)
    exchange = peewee.ForeignKeyField(Exchange)
    api_key = peewee.TextField()
    api_secret = peewee.TextField()
    api_password = peewee.TextField(null=True)
    active = peewee.BooleanField(default=True)

    def disable(self):
        info(
            f"disabled credential {self} for exchange {self.exchange.name} "
            f"of user {self.user.email}",
            notice=True,
        )
        self.user.send_message(f"disabled credential for exchange {self.exchange.name}")
        self.active = False
        self.save()
