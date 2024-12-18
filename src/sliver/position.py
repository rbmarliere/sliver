import datetime
from logging import info

import peewee

import sliver.database as db
from sliver.asset import Asset
from sliver.credential import Credential
from sliver.exceptions import DisablingError
from sliver.exchange_asset import ExchangeAsset
from sliver.exchanges.factory import ExchangeFactory
from sliver.market import Market
from sliver.order import Order
from sliver.strategies.factory import StrategyFactory
from sliver.strategies.status import StrategyStatus
from sliver.strategy import BaseStrategy, StrategySignals
from sliver.user_strategy import UserStrategy
from sliver.utils import get_next_refresh, get_return, get_roi


class Position(db.BaseModel):
    user_strategy = peewee.ForeignKeyField(UserStrategy)
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    next_bucket = peewee.DateTimeField(default=datetime.datetime.utcnow())
    bucket_max = peewee.BigIntegerField()
    bucket = peewee.BigIntegerField(default=0)
    status = peewee.TextField()
    target_amount = peewee.BigIntegerField(default=0)
    target_cost = peewee.BigIntegerField(default=0)
    entry_cost = peewee.BigIntegerField(default=0)
    entry_amount = peewee.BigIntegerField(default=0)
    entry_price = peewee.BigIntegerField(default=0)
    entry_time = peewee.DateTimeField(null=True)
    exit_time = peewee.DateTimeField(null=True)
    exit_price = peewee.BigIntegerField(default=0)
    exit_amount = peewee.BigIntegerField(default=0)
    exit_cost = peewee.BigIntegerField(default=0)
    fee = peewee.BigIntegerField(default=0)
    pnl = peewee.BigIntegerField(default=0)
    roi = peewee.DecimalField(default=0)
    last_high = peewee.BigIntegerField(default=0)
    last_low = peewee.BigIntegerField(default=0)
    refreshing = peewee.BooleanField(default=False)

    @classmethod
    def stop_all(cls):
        cls.update({cls.refreshing: False}).where(cls.refreshing).execute()

    @classmethod
    def get_all(cls):
        return cls.select().join(UserStrategy).join(BaseStrategy).order_by(cls.id)

    @classmethod
    def get_active(cls):
        return (
            cls.get_all()
            .where(BaseStrategy.status << StrategyStatus.active())
            .where(UserStrategy.active)
        )

    @classmethod
    def get_idle(cls):
        return cls.get_active().where(~cls.refreshing)

    @classmethod
    def get_opening(cls):
        return cls.get_idle().where(cls.status << ["open", "opening"])

    @classmethod
    def get_open(cls):
        return cls.get_all().where(cls.status << ["open", "opening", "closing"])

    @classmethod
    def get_pending(cls):
        return cls.get_idle().where(cls.next_refresh < datetime.datetime.utcnow())

    @classmethod
    def get_user_positions(self, user):
        base = Asset.alias()
        base_exchange_asset = ExchangeAsset.alias()
        quote = Asset.alias()
        quote_exchange_asset = ExchangeAsset.alias()
        return (
            Position.select(
                Position,
                BaseStrategy.id.alias("strategy_id"),
                BaseStrategy.side,
                Market.id.alias("market_id"),
                base.ticker.alias("base_ticker"),
                base_exchange_asset.precision.alias("base_precision"),
                quote.ticker.alias("quote_ticker"),
                quote_exchange_asset.precision.alias("quote_precision"),
                Market.amount_precision,
                Market.price_precision,
                peewee.Case(
                    None,
                    [((BaseStrategy.side == "long"), quote_exchange_asset.precision)],
                    base_exchange_asset.precision,
                ).alias("pnl_precision"),
            )
            .join(UserStrategy)
            .join(BaseStrategy)
            .join(Market)
            .join(base_exchange_asset, on=(Market.base_id == base_exchange_asset.id))
            .join(base, on=(base_exchange_asset.asset_id == base.id))
            .switch(Market)
            .join(quote_exchange_asset, on=(Market.quote_id == quote_exchange_asset.id))
            .join(quote, on=(quote_exchange_asset.asset_id == quote.id))
            .where(UserStrategy.user == user)
            .where(Position.entry_cost > 0)
            .where(Position.status != "deleted")
            .order_by(Position.id.desc())
        )

    @classmethod
    def get_open_user_positions(self, user):
        return self.get_open().where(UserStrategy.user == user)

    @classmethod
    def get_open_user_positions_by_exchange(self, user, exchange):
        return (
            self.get_open_user_positions(user)
            .join(Market)
            .join(ExchangeAsset, on=(Market.base_id == ExchangeAsset.id))
            .where(ExchangeAsset.exchange == exchange)
        )

    @classmethod
    def get_open_by_user_strategy(self, user_strategy):
        return self.get_open().where(Position.user_strategy == user_strategy)

    @property
    def exchange(self):
        if hasattr(self, "_exchange"):
            return self._exchange

        user = self.user_strategy.user
        exchange = self.user_strategy.strategy.market.base.exchange
        try:
            credential = user.get_active_credential(exchange).get()
        except Credential.DoesNotExist:
            raise DisablingError("no credential for exchange")

        exchange = ExchangeFactory.from_credential(credential)

        self._exchange = exchange
        return self._exchange

    def get_notice(self, prefix="", suffix=""):
        strategy = self.user_strategy.strategy
        p = self.exchange.api_fetch_last_price(strategy.symbol)

        return (
            f"{prefix}{strategy.side} position {self} of strategy {strategy} "
            f"in market {strategy.symbol} ({strategy.market.quote.exchange.name}) "
            f"{suffix}, last price is {p}"
        )

    def get_pnl(self):
        strategy = self.user_strategy.strategy
        market = strategy.market

        if self.entry_cost == 0 or self.entry_amount == 0:
            return 0

        if strategy.side == "long":
            return self.exit_cost - self.entry_cost - self.fee

        elif strategy.side == "short":
            avg_price = self.entry_price + self.exit_price / 2
            fee = market.base.div(self.fee, avg_price)
            return self.exit_amount - self.entry_amount - fee

    def get_roi(self):
        strategy = self.user_strategy.strategy

        if self.entry_cost == 0 or self.entry_amount == 0:
            return 0

        if strategy.side == "long":
            return get_roi(self.entry_cost, self.get_pnl())

        elif strategy.side == "short":
            return get_roi(self.entry_amount, self.get_pnl())

    def get_timedelta(self):
        if self.is_opening() or self.is_closing():
            return datetime.timedelta(0)
        orders = [o for o in self.get_orders()]
        if len(orders) > 1:
            t1 = orders[-1].time
            t2 = orders[0].time
            return t2 - t1
        return datetime.timedelta(0)

    def get_orders(self):
        return (
            Order.select(Order, BaseStrategy.id.alias("strategy_id"))
            .join(Position)
            .join(UserStrategy)
            .join(BaseStrategy)
            .where((Order.status != "canceled") | (Order.filled > 0))
            .where(Position.id == self.id)
            .order_by(Order.time.desc())
        )

    def get_orders_full(self):
        base = Asset.alias()
        base_exchange_asset = ExchangeAsset.alias()
        quote = Asset.alias()
        quote_exchange_asset = ExchangeAsset.alias()
        return (
            self.get_orders()
            .select(
                Order,
                BaseStrategy.id.alias("strategy_id"),
                base.ticker.alias("base_ticker"),
                base_exchange_asset.precision.alias("base_precision"),
                quote.ticker.alias("quote_ticker"),
                quote_exchange_asset.precision.alias("quote_precision"),
                Market.amount_precision,
                Market.price_precision,
            )
            .join(Market)
            .join(base_exchange_asset, on=(Market.base_id == base_exchange_asset.id))
            .join(base, on=(base_exchange_asset.asset_id == base.id))
            .switch(Market)
            .join(quote_exchange_asset, on=(Market.quote_id == quote_exchange_asset.id))
            .join(quote, on=(quote_exchange_asset.asset_id == quote.id))
            .order_by(Order.time.desc())
        )

    def get_open_orders(self):
        query = self.get_orders().where(Order.status == "open")
        return [order for order in query]

    def is_pending(self):
        return self.is_opening() or self.is_closing()

    def is_open(self):
        return self.status == "open" or self.status == "opening"

    def is_opening(self):
        return self.status == "opening"

    def is_closing(self):
        return self.status == "closing" or self.status == "stopping"

    def is_closed(self):
        return (
            self.status == "closed"
            or self.status == "stopped"
            or self.status == "stalled"
        )

    def is_stopping(self):
        return self.status == "stopping"

    def is_stopped(self):
        return self.status == "stopped"

    def is_buying(self):
        strategy = self.user_strategy.strategy
        return (strategy.side == "long" and self.is_opening()) or (
            strategy.side == "short" and self.is_closing()
        )

    def is_selling(self):
        strategy = self.user_strategy.strategy
        return (strategy.side == "long" and self.is_closing()) or (
            strategy.side == "short" and self.is_opening()
        )

    def get_bucket_max(self):
        strategy = self.user_strategy.strategy
        market = strategy.market

        if self.is_opening():
            if strategy.side == "long":
                if self.is_stopping():
                    engine = strategy.stop_engine
                else:
                    engine = strategy.buy_engine

                if engine.min_buckets <= 1:
                    return self.target_cost - self.entry_cost

                return market.quote.div(
                    self.target_cost - self.entry_cost,
                    market.quote.transform(engine.min_buckets),
                    prec=strategy.market.price_precision,
                )

            elif strategy.side == "short":
                if self.is_stopping():
                    engine = strategy.stop_engine
                else:
                    engine = strategy.sell_engine

                if engine.min_buckets <= 1:
                    return self.target_amount - self.entry_amount

                return market.base.div(
                    self.target_amount - self.entry_amount,
                    market.base.transform(engine.min_buckets),
                    prec=strategy.market.amount_precision,
                )

        elif self.is_closing():
            if strategy.side == "long":
                if self.is_stopping():
                    engine = strategy.stop_engine
                else:
                    engine = strategy.sell_engine

                if engine.min_buckets <= 1:
                    return self.entry_amount

                return market.base.div(
                    self.entry_amount,
                    market.base.transform(engine.min_buckets),
                    prec=strategy.market.amount_precision,
                )

            elif strategy.side == "short":
                if self.is_stopping():
                    engine = strategy.stop_engine
                else:
                    engine = strategy.buy_engine

                if engine.min_buckets <= 1:
                    return self.entry_amount

                return market.quote.div(
                    self.entry_cost,
                    market.quote.transform(engine.min_buckets),
                    prec=strategy.market.price_precision,
                )

    def get_remaining_cost(self, last_price):
        market = self.user_strategy.strategy.market

        remaining_to_fill = self.bucket_max - self.bucket
        if remaining_to_fill <= 0:
            return 0

        if self.is_opening():
            remaining = self.target_cost - self.entry_cost
        elif self.is_closing():
            remaining = self.entry_cost - self.exit_cost

        remaining = min(remaining, remaining_to_fill)

        remainder_c = remaining - remaining_to_fill
        remainder_a = market.base.div(remainder_c, last_price)
        if remainder_c > 0 and (
            remainder_c <= market.cost_min or remainder_a <= market.amount_min
        ):
            info(f"remainder is {market.quote.print(remainder_c)}")
            remaining = remainder_c

        user = self.user_strategy.user
        balance = user.get_exchange_balance(market.quote, sync=True)

        remaining = min(remaining, balance.total)

        info(f"bucket cost is {market.quote.print(self.bucket)}")
        info(f"balance is {market.quote.print(balance.total)}")
        info(f"remaining to fill in bucket is {market.quote.print(remaining_to_fill)}")
        info(f"remaining is {market.quote.print(remaining)}")

        return remaining

    def get_remaining_amount(self, last_price):
        market = self.user_strategy.strategy.market

        remaining_to_fill = self.bucket_max - self.bucket
        if remaining_to_fill <= 0:
            return 0

        if self.is_opening():
            remaining = self.target_amount - self.entry_amount
        elif self.is_closing():
            remaining = self.entry_amount - self.exit_amount

        remaining = min(remaining, remaining_to_fill)

        remainder_a = remaining - remaining_to_fill
        remainder_c = market.base.format(remainder_a) * last_price
        if remainder_a > 0 and (
            remainder_c <= market.cost_min or remainder_a <= market.amount_min
        ):
            info(f"remainder is {market.base.print(remainder_a)}")
            remaining = remainder_a

        user = self.user_strategy.user
        balance = user.get_exchange_balance(market.base, sync=True)

        remaining = min(remaining, balance.total)

        info(f"bucket amount is {market.base.print(self.bucket)}")
        info(f"remaining to fill in bucket is {market.base.print(remaining_to_fill)}")
        info(f"remaining is {market.base.print(remaining)}")
        info(f"balance is {market.base.print(balance.total)}")

        return remaining

    def open(u_st, status="opening"):
        user = u_st.user
        strategy = u_st.strategy
        market = strategy.market

        if strategy.side == "long":
            engine = strategy.buy_engine
        elif strategy.side == "short":
            engine = strategy.sell_engine

        pos = Position(
            user_strategy=u_st,
            status=status,
            next_bucket=get_next_refresh(engine.bucket_interval),
            entry_time=datetime.datetime.utcnow(),
        )

        if strategy.stop_engine:
            cooldown = strategy.stop_engine.stop_cooldown
            last_pos = (
                Position.select()
                .where(Position.user_strategy == u_st)
                .order_by(Position.id.desc())
                .get_or_none()
            )
            if last_pos and last_pos.is_stopped():
                c = datetime.datetime.utcnow() - last_pos.exit_time
                if c < datetime.timedelta(minutes=cooldown):
                    info("cooled down, can't create position")
                    return

        p = pos.exchange.api_fetch_last_price(strategy.symbol)
        last_price = market.quote.transform(p)

        pos.exchange.sync_user_balance(user)

        if strategy.side == "long":
            pos.entry_amount, pos.target_cost = user.get_free_balances(strategy)

            if pos.entry_amount > 0:
                pos.entry_price = last_price
                pos.entry_cost = market.base.format(pos.entry_amount) * last_price
                pos.target_cost += pos.entry_cost

            info(f"target_cost is {market.quote.print(pos.target_cost)}")
            info(f"entry_amount is {market.base.print(pos.entry_amount)}")

            if status == "closing" and not market.is_valid_amount(
                pos.entry_amount, last_price
            ):
                info("invalid entry_amount, can't create 'closing' position")
                return

            if pos.target_cost == 0 or pos.target_cost <= strategy.market.cost_min:
                info("invalid target_cost, can't create position")
                return

        elif strategy.side == "short":
            pos.target_amount, pos.entry_cost = user.get_free_balances(strategy)

            if pos.entry_cost > 0:
                pos.entry_price = last_price
                pos.entry_amount = market.base.div(pos.entry_cost, last_price)
                pos.target_amount += pos.entry_amount

            info(f"target_amount is {market.base.print(pos.target_amount)}")
            info(f"entry_cost is {market.quote.print(pos.entry_cost)}")

            if status == "closing" and pos.entry_cost <= strategy.market.cost_min:
                info("invalid entry_cost, can't create 'closing' position")
                return

            if not market.is_valid_amount(pos.target_amount, last_price):
                info("invalid target_amount, can't create position")
                return

        pos.bucket_max = pos.get_bucket_max()
        pos.save()

        info(f"opening position {pos.id}")
        user.send_message(pos.get_notice(prefix="opening "))

        return pos

    def close(self):
        info(f"closing position {self}")
        user = self.user_strategy.user
        user.send_message(self.get_notice(prefix="closing "))

        self.bucket = 0
        self.status = "closing"
        self.bucket_max = self.get_bucket_max()

        self.save()

    def resume(self):
        info(f"reopening position {self}")
        user = self.user_strategy.user
        user.send_message(self.get_notice(prefix="reopening "))

        self.bucket = 0
        self.status = "opening"
        self.bucket_max = self.get_bucket_max()

        self.save()

    def disable(self):
        self.user_strategy.disable()

    def postpone(self, interval_in_minutes=None):
        if interval_in_minutes is None:
            if self.status == "opening":
                n = self.user_strategy.strategy.buy_engine.refresh_interval
            elif self.status == "closing":
                n = self.user_strategy.strategy.sell_engine.refresh_interval
            else:
                n = 99999
            interval_in_minutes = n
        self.next_refresh = get_next_refresh(interval_in_minutes)
        info(f"postponed position {self} next refresh at {self.next_refresh}")
        self.save()

    def stop(self, last_price=None):
        strategy = self.user_strategy.strategy
        engine = strategy.stop_engine
        market = strategy.market
        user = self.user_strategy.user

        info(f"stopping position {self}")
        info(f"last price is {market.quote.print(last_price)}")
        info(f"high was {market.quote.print(self.last_high)}")
        info(f"low was {market.quote.print(self.last_low)}")
        info(f"stop gain is {engine.stop_gain}, trailing is {engine.trailing_gain}")
        info(f"stop loss is {engine.stop_loss}, trailing is {engine.trailing_loss}")

        user.send_message(self.get_notice(prefix="stopped "))

        self.status = "stopping"
        self.close()

        self.save()

    def stall(self):
        symbol = self.user_strategy.strategy.symbol
        for o in self.get_open_orders():
            self.exchange.api_cancel_orders(symbol, oid=o.exchange_order_id)
        self.status = "stalled"
        self.save()
        self.user_strategy.user.send_message(self.get_notice(prefix="stalled "))

    def drop(self):
        symbol = self.user_strategy.strategy.symbol
        for o in self.get_open_orders():
            self.exchange.api_cancel_orders(symbol, oid=o.exchange_order_id)
        self.status = "deleted"
        self.save()

    def refresh_stops(self, last_price=None):
        strategy = self.user_strategy.strategy
        engine = strategy.stop_engine
        market = strategy.market

        if not engine:
            return False

        if not self.is_open():
            return False

        if self.entry_price == 0:
            return False

        if engine.stop_gain <= 0 and engine.stop_loss <= 0:
            return False

        if last_price is None:
            p = self.exchange.api_fetch_last_price(strategy.symbol)
            last_price = market.quote.transform(p)

        if last_price > self.last_high:
            self.last_high = last_price
            self.save()
        if last_price < self.last_low or self.last_low == 0:
            self.last_low = last_price
            self.save()

        ret_p = get_return(self.entry_price, last_price)
        ret_h = get_return(self.last_high, last_price)
        ret_l = get_return(self.last_low, last_price)

        if engine.stop_gain > 0:
            if strategy.side == "long":
                if engine.trailing_gain:
                    if ret_h * -1 > engine.stop_gain:
                        self.stop(last_price)
                        return True
                else:
                    if ret_p > engine.stop_gain:
                        self.stop(last_price)
                        return True
            elif strategy.side == "short":
                if engine.trailing_gain:
                    if ret_l > engine.stop_gain:
                        self.stop(last_price)
                        return True
                else:
                    if ret_p * -1 > engine.stop_gain:
                        self.stop(last_price)
                        return True

        if engine.stop_loss > 0:
            if strategy.side == "long":
                if engine.trailing_loss:
                    if ret_l > engine.stop_loss:
                        self.stop(last_price)
                        return True
                else:
                    if ret_p * -1 > engine.stop_loss:
                        self.stop(last_price)
                        return True
            elif strategy.side == "short":
                if engine.trailing_loss:
                    if ret_h * -1 > engine.stop_loss:
                        self.stop(last_price)
                        return True
                else:
                    if ret_p > engine.stop_loss:
                        self.stop(last_price)
                        return True

        return False

    def check_stops(self):
        if self.refresh_stops():
            self.refresh()

    def add_order(self, order):
        strategy = self.user_strategy.strategy
        market = strategy.market

        if strategy.side == "long":
            self.bucket += order.cost
        elif strategy.side == "short":
            self.bucket += order.filled

        if (strategy.side == "long" and order.side == "buy") or (
            strategy.side == "short" and order.side == "sell"
        ):
            self.entry_cost += order.cost
            self.entry_amount += order.filled
            self.fee += order.fee
            if self.entry_amount > 0:
                self.entry_price = market.base.div(self.entry_cost, self.entry_amount)

        elif (strategy.side == "long" and order.side == "sell") or (
            strategy.side == "short" and order.side == "buy"
        ):
            self.exit_amount += order.filled
            self.exit_cost += order.cost
            self.fee += order.fee
            if self.exit_amount > 0:
                self.exit_price = market.base.div(self.exit_cost, self.exit_amount)

        self.save()

    def sync_limit_orders(self):
        # fetch internal open orders
        orders = self.get_open_orders()

        # if no orders found, exit
        if len(orders) == 0:
            info("no open orders found")
            return

        for order in orders:
            oid = order.exchange_order_id

            self.exchange.api_cancel_orders(self.user_strategy.strategy.symbol, oid=oid)

            order = self.exchange.get_synced_order(self, oid)

            if order.status != "open":
                self.add_order(order)

    def refresh(self):
        if not self.user_strategy.active or self.refreshing:
            return

        with db.connection.atomic():
            self.refreshing = True
            self.save()

        strategy = StrategyFactory.from_base(self.user_strategy.strategy)
        signal = strategy.get_signal()
        market = strategy.market
        BUY = StrategySignals.BUY
        SELL = StrategySignals.SELL

        p = self.exchange.api_fetch_last_price(strategy.symbol)
        last_price = market.quote.transform(p)

        info("___________________________________________")
        info(f"refreshing {self.status} {strategy.side} position {self}")
        info(f"user is {self.user_strategy.user}")
        info(f"strategy is {self.user_strategy.strategy}")
        info(f"last price: {strategy.market.quote.print(last_price)}")
        info(f"target cost is {market.quote.print(self.target_cost)}")
        info(f"target amount is {market.base.print(self.target_amount)}")
        info(f"entry cost is {market.quote.print(self.entry_cost)}")
        info(f"entry amount is {market.base.print(self.entry_amount)}")
        info(f"exit cost is {market.quote.print(self.exit_cost)}")
        info(f"exit amount is {market.base.print(self.exit_amount)}")

        self.sync_limit_orders()

        self.refresh_stops(last_price)

        if (
            self.entry_cost > 0
            and self.is_open()
            and (
                (strategy.side == "long" and signal == SELL)
                or (strategy.side == "short" and signal == BUY)
            )
        ):
            self.close()

        if (
            self.entry_cost > 0
            and self.is_closing()
            and (
                (strategy.side == "long" and signal == BUY)
                or (strategy.side == "short" and signal == SELL)
            )
        ):
            self.resume()

        if self.is_opening() or self.is_closing():
            self.refresh_bucket(last_price)

        self.refresh_status(last_price)

        self.postpone()

        self.refreshing = False
        self.save()

    def refresh_bucket(self, last_price):
        strategy = self.user_strategy.strategy
        market = strategy.market
        now = datetime.datetime.utcnow()

        if self.is_stopping():
            engine = strategy.stop_engine
        elif self.is_buying():
            engine = strategy.buy_engine
        elif self.is_selling():
            engine = strategy.sell_engine

        info(f"next bucket at {self.next_bucket}")

        if now > self.next_bucket:
            next_bucket = get_next_refresh(engine.bucket_interval)
            self.next_bucket = next_bucket
            self.bucket = 0
            info(f"moving on to next bucket at {self.next_bucket}")

        info(f"limit to market ratio is {engine.lm_ratio}")

        if self.is_buying():
            remaining_cost = self.get_remaining_cost(last_price)
            remaining_amount = market.base.div(
                remaining_cost, last_price, prec=market.amount_precision
            )

            m_total_cost = int(engine.lm_ratio * remaining_cost)
            m_total_amount = market.base.div(
                m_total_cost, last_price, prec=market.amount_precision
            )

            # slippage TODO: check books first?
            m_total_amount *= 0.99

        elif self.is_selling():
            remaining_amount = self.get_remaining_amount(last_price)
            remaining_cost = market.base.format(remaining_amount) * last_price

            m_total_amount = int(engine.lm_ratio * remaining_amount)

        if now < self.next_bucket and (
            remaining_cost <= market.cost_min or remaining_amount <= market.amount_min
        ):
            info("bucket is full")
            return

        inserted_orders = False

        if self.is_buying():
            side = "buy"

            if m_total_amount > 0:
                inserted_orders = self.exchange.create_order(
                    self, "market", side, m_total_amount, last_price
                )

            if engine.lm_ratio < 1:
                l_total = self.get_remaining_cost(last_price)
                if l_total > 0:
                    inserted_orders = self.exchange.create_limit_buy_orders(
                        self, l_total, last_price, engine.num_orders, engine.spread
                    )

        elif self.is_selling():
            side = "sell"

            if m_total_amount > 0:
                inserted_orders = self.exchange.create_order(
                    self, "market", side, m_total_amount, last_price
                )

            if engine.lm_ratio < 1:
                l_total = self.get_remaining_amount(last_price)
                if l_total > 0:
                    inserted_orders = self.exchange.create_limit_sell_orders(
                        self, l_total, last_price, engine.num_orders, engine.spread
                    )

        # if bucket is not full but can't insert new orders, fill at market
        if not inserted_orders:
            inserted_orders = self.exchange.create_order(
                self, "market", side, remaining_amount, last_price
            )

        if not inserted_orders:
            self.user_strategy.user.send_message(
                self.get_notice(prefix="could not insert any orders for ")
            )

    def refresh_status(self, last_price):
        strategy = self.user_strategy.strategy
        market = strategy.market
        user = self.user_strategy.user

        cost_diff = self.entry_cost - self.exit_cost
        amount_diff = self.entry_amount - self.exit_amount
        cost_diff_amount = market.base.div(cost_diff, last_price)
        amount_diff_cost = market.base.format(amount_diff) * last_price

        if self.is_closing() and (
            cost_diff <= market.cost_min
            or cost_diff_amount <= market.amount_min
            or amount_diff <= market.amount_min
            or amount_diff_cost <= market.cost_min
        ):
            self.status = "closed"
            self.pnl = self.get_pnl()
            self.roi = self.get_roi()
            self.exit_time = datetime.datetime.utcnow()
            info("position is now closed")
            user.send_message(
                self.get_notice(prefix="closed ", suffix=f" ROI: {self.roi}%")
            )

        cost_diff = self.target_cost - self.entry_cost
        cost_diff_amount = market.base.div(cost_diff, last_price)
        amount_diff = self.target_amount - self.entry_amount
        amount_diff_cost = market.base.format(amount_diff) * last_price

        if self.is_opening() and (
            (
                strategy.side == "long"
                and (
                    cost_diff <= market.cost_min
                    or cost_diff_amount <= market.amount_min
                )
            )
            or (
                strategy.side == "short"
                and (
                    amount_diff <= market.amount_min
                    or amount_diff_cost <= market.cost_min
                )
            )
        ):
            self.status = "open"
            info("position is now open")
            user.send_message(self.get_notice(prefix="opened "))

        self.save()
