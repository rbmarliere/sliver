import datetime
from logging import info

import peewee

import sliver.database as db
from sliver.exchange import Exchange
from sliver.exchange_asset import ExchangeAsset
from sliver.market import Market
from sliver.strategies.signals import StrategySignals
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

        u_st = cls.get_or_create(user=user, strategy=strategy)[0]
        u_st.active = subscribed
        u_st.save()

        if not u_st.active:
            p = u_st.position
            if p is not None:
                p.stall()

        return u_st

    @property
    def position(self):
        from sliver.position import Position

        return Position.get_open_by_user_strategy(self).get_or_none()

    def open_position(self, status="opening"):
        from sliver.position import Position

        if not self.active:
            info("can't open position, user_strategy is not active")
            return

        if self.position:
            info("can't open position, position already open")
            return

        return Position.open(self, status)

    def disable(self):
        info(
            f"disabled user {self.user.email} strategy {self.strategy.description}",
        )
        self.user.send_message(f"disabled strategy {self.strategy.id}")
        self.active = False
        self.save()

    def refresh(self, signal):
        if not self.active:
            return

        info("...........................................")
        info(f"refreshing user {self.user}")

        pos = self.position

        if pos:
            pos.next_refresh = datetime.datetime.utcnow()
            pos.save()

        else:
            if (self.strategy.side == "long" and signal == StrategySignals.BUY) or (
                self.strategy.side == "short" and signal == StrategySignals.SELL
            ):
                self.open_position()

            if (self.strategy.side == "long" and signal == StrategySignals.SELL) or (
                self.strategy.side == "short" and signal == StrategySignals.BUY
            ):
                p = self.open_position(status="closing")
                if p is not None:
                    p.close()
