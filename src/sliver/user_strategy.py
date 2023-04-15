import datetime

import peewee

import sliver.database as db
from sliver.exceptions import MarketAlreadySubscribed
from sliver.exchange import Exchange
from sliver.exchange_asset import ExchangeAsset
from sliver.market import Market
from sliver.print import print
from sliver.strategies.signals import StrategySignals
from sliver.strategy import BaseStrategy
from sliver.user import User


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
    def get_by_exchange(cls, user, exchange):
        return (
            cls.get_active_user(user)
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
        print(
            f"disabled user {self.user.email} strategy {self.strategy.description}",
            notice=True,
        )
        self.user.send_message(f"disabled strategy {self.strategy.id}")
        self.active = False
        self.save()

    def refresh(self):
        from sliver.position import Position

        strategy = self.strategy
        BUY = StrategySignals.BUY
        SELL = StrategySignals.SELL

        print("...........................................")
        print(f"refreshing user {self.user} strategy {self}")

        # sync orders of active position
        position = (
            Position.get_open()
            .where(UserStrategy.user_id == self.user_id)
            .where(UserStrategy.strategy_id == self.strategy_id)
            .get_or_none()
        )

        if position is None:
            if strategy.get_signal() == BUY:
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

                t_cost = self.get_target_cost()

                if t_cost == 0 or t_cost < strategy.market.cost_min:
                    print("invalid target_cost, can't create position")
                    return

                Position.open(self, t_cost)

        elif position.is_open() and strategy.get_signal() == SELL:
            position.next_refresh = datetime.datetime.utcnow()
            position.save()

    def get_target_cost(self):
        from sliver.position import Position

        user = self.user
        exchange = self.strategy.market.base.exchange
        m_print = self.strategy.market.quote.print
        transform = self.strategy.market.quote.transform

        inventory = user.get_inventory()

        # TODO currently, quote can only be USDT
        available_in_exch = user.get_exchange_balance(self.strategy.market.quote)
        if not available_in_exch:
            available_in_exch = 0
        else:
            cash_in_exch = available_in_exch.total
        quote = self.strategy.market.quote.asset.ticker
        print(
            f"available {quote} in exchange {exchange.name} is {m_print(cash_in_exch)}"
        )

        available = cash_in_exch * (1 - user.cash_reserve)
        print(f"available minus reserve is {m_print(available)}")

        active_strat_in_exch = self.get_by_exchange(user, exchange).count()
        pos_curr_cost = [
            p.entry_cost
            for p in Position.get_open_user_positions_by_exchange(user, exchange)
        ]
        available = (available + sum(pos_curr_cost)) / active_strat_in_exch
        print(f"available for strategy is {m_print(available)}")

        max_risk = transform(inventory["max_risk"])
        target_cost = min(max_risk, available)
        print(f"max risk is {m_print(max_risk)}")
        print(f"target cost is {m_print(target_cost)}")

        return int(target_cost)
