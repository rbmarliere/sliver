import peewee

import sliver.database as db
from sliver.exchange import Exchange
from sliver.exchange_asset import ExchangeAsset
from sliver.market import Market
from sliver.print import print
from sliver.strategy import BaseStrategy


class UserStrategy(db.BaseModel):
    user = peewee.DeferredForeignKey("User", null=True)
    strategy = peewee.ForeignKeyField(BaseStrategy)
    active = peewee.BooleanField(default=False)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, strategy_id)")]

    @classmethod
    def get_by_exchange(cls, user, exchange):
        return (
            cls.select()
            .where(cls.active)
            .where(cls.user == user)
            .join(BaseStrategy)
            .join(Market)
            .join(ExchangeAsset, on=(Market.base_id == ExchangeAsset.id))
            .join(Exchange)
            .where(Exchange.id == exchange.id)
        )

    @classmethod
    def subscribe(cls, user, strategy, subscribed=None):
        if subscribed is None:
            subscribed = False

        # if subscribed:
        #     if (
        #         cls.select()
        #         .where(cls.active)
        #         .where(cls.user == user)
        #         .join(BaseStrategy)
        #         .where(BaseStrategy.market == strategy.market)
        #         .exists()
        #     ):
        #         raise MarketAlreadySubscribed

        u_st = cls.get_or_create(user=user, strategy=strategy)[0]
        u_st.active = subscribed
        u_st.save()

        return u_st

    def disable(self):
        print(
            f"disabled user {self.user.email} strategy {self.strategy.description}",
            notice=True,
        )
        self.user.send_message(f"disabled strategy {self.strategy.id}")
        self.active = False
        self.save()
