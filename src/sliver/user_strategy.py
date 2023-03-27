import datetime

import peewee

import sliver.database as db
from sliver.exceptions import MarketAlreadySubscribed
from sliver.print import print
from sliver.strategies.signals import StrategySignals
from sliver.user import User
from sliver.strategy import BaseStrategy


class UserStrategy(db.BaseModel):
    user = peewee.ForeignKeyField(User)
    strategy = peewee.ForeignKeyField(BaseStrategy)
    active = peewee.BooleanField(default=False)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, strategy_id)")]

    @classmethod
    def get_active(cls):
        return cls.select().where(cls.active)

    @classmethod
    def get_active_strategy(cls, strategy):
        return cls.get_active().where(cls.strategy == strategy)

    @classmethod
    def get_active_user(cls, user):
        return cls.get_active().where(cls.user == user)

    @classmethod
    def subscribe(cls, user, strategy, subscribed=None):
        if subscribed is None:
            subscribed = False

        if subscribed:
            if (
                cls.get_active_user(user)
                .join(BaseStrategy)
                .where(BaseStrategy.market == strategy.market)
                .exists()
            ):
                raise MarketAlreadySubscribed

        u_st = cls.get_or_create(user=user, strategy=strategy)[0]
        u_st.active = subscribed
        u_st.save()

        return u_st

    def disable(self):
        print("disabling user's strategy {s}...".format(s=self))
        self.user.send_message("disabled strategy {s}".format(s=self.strategy.id))
        self.active = False
        self.save()

    def refresh(self):
        from sliver.position import Position

        strategy = self.strategy
        BUY = StrategySignals.BUY
        SELL = StrategySignals.SELL

        print("...........................................")
        print("refreshing user {u} strategy {s}".format(u=self.user, s=self))

        # sync orders of active position
        position = (
            Position.get_open()
            .where(UserStrategy.user_id == self.user_id)
            .where(UserStrategy.strategy_id == self.strategy_id)
            .get_or_none()
        )

        if position is None:
            if strategy.signal == BUY:
                if strategy.stop_engine:
                    cooldown = strategy.stop_engine.stop_cooldown
                    last_pos = (
                        Position.get_active()
                        .where(UserStrategy.user_id == self.user_id)
                        .where(UserStrategy.strategy_id == self.strategy_id)
                        .order_by(Position.id.desc())
                        .get_or_none()
                    )
                    if last_pos and last_pos.stopped:
                        c = datetime.datetime.utcnow() - last_pos.exit_time
                        if c < datetime.timedelta(minutes=cooldown):
                            print("cooled down, can't create position")
                            return

                t_cost = self.user.get_target_cost(self.strategy)

                jls_extract_var = t_cost
                if t_cost == 0 or jls_extract_var < strategy.market.cost_min:
                    print("invalid target_cost, can't create position")
                    return

                Position.open(self, t_cost)

        elif position.is_open() and strategy.signal == SELL:
            position.next_refresh = datetime.datetime.utcnow()
            position.save()
