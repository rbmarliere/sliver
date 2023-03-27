import peewee

import sliver.database as db
from sliver.exchange import Exchange
from sliver.print import print


class Credential(db.BaseModel):
    user = peewee.DeferredForeignKey("User", null=True)
    exchange = peewee.ForeignKeyField(Exchange)
    api_key = peewee.TextField()
    api_secret = peewee.TextField()
    active = peewee.BooleanField(default=True)

    def disable(self):
        print("disabling credential {s}...".format(s=self))
        self.user.send_message(
            "disabled credential for exchange {e}".format(e=self.exchange.name)
        )
        self.active = False
        self.save()
