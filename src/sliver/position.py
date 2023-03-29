import datetime

import peewee

import sliver.database as db
from sliver.asset import Asset
from sliver.credential import Credential
from sliver.exceptions import DisablingError
from sliver.exchange_asset import ExchangeAsset
from sliver.exchanges.factory import ExchangeFactory
from sliver.market import Market
from sliver.order import Order
from sliver.print import print
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
    target_cost = peewee.BigIntegerField()
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
    stopped = peewee.BooleanField(default=False)

    @classmethod
    def get_active(cls):
        return (
            cls.select()
            .join(UserStrategy)
            .join(BaseStrategy)
            .where(BaseStrategy.active)
            .where(UserStrategy.active)
            .order_by(cls.id)
        )

    @classmethod
    def get_opening(cls):
        return cls.get_active().where(cls.status << ["open", "opening"])

    @classmethod
    def get_open(cls):
        return cls.get_active().where(cls.status << ["open", "opening", "closing"])

    @classmethod
    def get_pending(cls):
        return cls.get_open().where(cls.next_refresh < datetime.datetime.utcnow())

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
                Market.id.alias("market_id"),
                base.ticker.alias("base_ticker"),
                base_exchange_asset.precision.alias("base_precision"),
                quote.ticker.alias("quote_ticker"),
                quote_exchange_asset.precision.alias("quote_precision"),
                Market.amount_precision,
                Market.price_precision,
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
        market = self.user_strategy.strategy.market
        p = self.exchange.api_fetch_last_price(market.get_symbol())

        return (
            "{p}position {pid} of strategy {s} in market {m} ({e}) {su}, "
            "last price is {lp}".format(
                p=prefix,
                pid=self.id,
                s=self.user_strategy.strategy,
                m=market.get_symbol(),
                e=market.quote.exchange.name,
                su=suffix,
                lp=p,
            )
        )

    def get_timedelta(self):
        if self.is_pending():
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

    def is_open(self):
        return self.status == "open" or self.status == "opening"

    def is_pending(self):
        return self.status == "opening" or self.status == "closing"

    def get_remaining_to_fill(self):
        return self.bucket_max - self.bucket

    def get_remaining_to_exit(self):
        return self.entry_amount - self.exit_amount

    def get_remaining_cost(self):
        market = self.user_strategy.strategy.market

        remaining_to_fill = self.bucket_max - self.bucket
        remaining_to_open = self.target_cost - self.entry_cost
        remaining = min(abs(remaining_to_fill), abs(remaining_to_open))
        remaining = 0 if remaining_to_fill < 0 else remaining

        user = self.user_strategy.user
        balance = user.get_exchange_balance(market.quote, sync=True)
        remaining = min(remaining, balance.total)

        print("bucket cost is {a}".format(a=market.quote.print(self.bucket)))
        print(
            "remaining to fill in bucket is {r}".format(r=market.quote.print(remaining))
        )
        print("balance is {r}".format(r=market.quote.print(balance.total)))

        return remaining

    def get_remaining_amount(self, last_price):
        market = self.user_strategy.strategy.market

        remaining_to_fill = self.get_remaining_to_fill()
        remaining_to_exit = self.get_remaining_to_exit()
        remaining = min(abs(remaining_to_fill), abs(remaining_to_exit))
        remaining = 0 if remaining_to_fill < 0 else remaining

        user = self.user_strategy.user
        balance = user.get_exchange_balance(market.base, sync=True)
        remaining = min(remaining, balance.total)

        print("bucket amount is {a}".format(a=market.base.print(self.bucket)))
        print(
            "remaining to fill in bucket is {r}".format(
                r=market.base.print(remaining_to_fill)
            )
        )
        print(
            "remaining to exit position is {r}".format(
                r=market.base.print(remaining_to_exit)
            )
        )
        print("balance is {r}".format(r=market.base.print(balance.total)))

        # avoid position rounding errors by exiting early
        r = remaining_to_exit - remaining_to_fill
        position_remainder = market.base.format(r)
        if (
            position_remainder > 0
            and position_remainder * last_price <= market.cost_min
        ):
            print("position remainder is {r}".format(r=market.base.print(r)))
            remaining = remaining_to_exit

        return remaining

    def open(u_st, t_cost: int):
        strategy = u_st.strategy
        engine = strategy.buy_engine
        market = strategy.market
        user = u_st.user
        next_bucket = get_next_refresh(engine.bucket_interval)

        if engine.min_buckets > 0:
            bucket_max = market.quote.div(
                t_cost,
                market.quote.transform(engine.min_buckets),
                prec=strategy.market.price_precision,
            )
        else:
            bucket_max = t_cost

        position = Position(
            user_strategy=u_st,
            next_bucket=next_bucket,
            bucket_max=bucket_max,
            status="opening",
            target_cost=t_cost,
            entry_time=datetime.datetime.utcnow(),
        )
        position.save()

        print("opening position {i}".format(i=position.id))
        user.send_message(position.get_notice(prefix="opening "))

        return position

    def close(self, engine=None):
        strategy = self.user_strategy.strategy
        market = strategy.market
        user = self.user_strategy.user

        if engine is None:
            engine = strategy.sell_engine

        if engine.min_buckets > 0:
            self.bucket_max = market.base.div(
                self.entry_amount,
                market.base.transform(engine.min_buckets),
                prec=strategy.market.amount_precision,
            )
        else:
            self.bucket_max = self.entry_amount

        self.bucket = 0
        self.status = "closing"

        print("closing position {i}".format(i=self.id))
        user.send_message(self.get_notice(prefix="closing "))

        self.save()

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
        print(
            "postponed position {i} next refresh at {n}".format(
                i=self.id, n=self.next_refresh
            )
        )
        self.save()

    def stop(self, last_price=None):
        strategy = self.user_strategy.strategy
        engine = strategy.stop_engine
        market = strategy.market
        user = self.user_strategy.user

        print(
            "last price is {p}, high was {h} and low was {l}".format(
                p=market.quote.print(last_price),
                h=market.quote.print(self.last_high),
                l=market.quote.print(self.last_low),
            )
        )
        print(
            "stop gain is {g}, trailing is {gt}".format(
                g=engine.stop_gain, gt=engine.trailing_gain
            )
        )
        print(
            "stop loss is {l}, trailing is {lt}".format(
                l=engine.stop_loss, lt=engine.trailing_loss
            )
        )
        user.send_message(self.get_notice(prefix="stopped "))
        self.stopped = True
        self.close(engine=engine)
        self.save()

    def check_stops(self, last_price=None):
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
            p = self.exchange.api_fetch_last_price(market.get_symbol())
            last_price = market.quote.transform(p)

        if last_price > self.last_high:
            self.last_high = last_price
            self.save()
        if last_price < self.last_low or self.last_low == 0:
            self.last_low = last_price
            self.save()

        if engine.stop_gain > 0:
            cur_gain = 0

            if engine.trailing_gain:
                # multiply by -1 because when taken from the high, its negative
                # if price is lower than entry, there are no gains to stop
                if last_price > self.entry_price:
                    cur_gain = get_return(self.last_high, last_price) * -1
            else:
                cur_gain = get_return(self.entry_price, last_price)

            if cur_gain > engine.stop_gain:
                self.stop(last_price=last_price)
                return True

        if engine.stop_loss > 0:
            cur_loss = 0

            if engine.trailing_loss:
                # if price is higher than entry, there are no losses to stop
                if last_price < self.entry_price:
                    cur_loss = get_return(self.last_low, last_price)
            else:
                # multiply by -1 because strategy.stop_loss is stored positive
                cur_loss = get_return(self.entry_price, last_price) * -1

            if cur_loss > engine.stop_loss:
                self.stop(last_price=last_price)
                return True

        return False

    def add_order(self, order):
        market = self.user_strategy.strategy.market

        if order.side == "buy":
            self.bucket += order.cost
            self.entry_cost += order.cost
            self.entry_amount += order.filled
            self.fee += order.fee

            if self.entry_amount > 0:
                self.entry_price = market.quote.div(self.entry_cost, self.entry_amount)

        elif order.side == "sell":
            self.bucket += order.filled
            self.exit_amount += order.filled
            self.exit_cost += order.cost
            self.fee += order.fee

            if self.exit_amount > 0:
                self.exit_price = market.quote.div(self.exit_cost, self.exit_amount)

        self.save()

    def sync_limit_orders(self):
        # fetch internal open orders
        orders = self.get_open_orders()

        # if no orders found, exit
        if len(orders) == 0:
            print("no open orders found")
            return

        for order in orders:
            oid = order.exchange_order_id

            self.exchange.api_cancel_orders(
                self.user_strategy.strategy.market.get_symbol(), oid=oid
            )

            order = self.exchange.get_synced_order(self, oid)

            if order.status != "open":
                self.add_order(order)

    def refresh(self):
        if not self.user_strategy.active:
            return

        strategy = self.user_strategy.strategy
        signal = strategy.get_signal()
        market = strategy.market
        SELL = StrategySignals.SELL

        p = self.exchange.api_fetch_last_price(market.get_symbol())
        last_p = market.quote.transform(p)

        print("___________________________________________")
        print("refreshing {s} position {i}".format(s=self.status, i=self.id))
        print("strategy is {s}".format(s=self.user_strategy.strategy.id))
        print("last price: {p}".format(p=strategy.market.quote.print(last_p)))
        print("target cost is {t}".format(t=market.quote.print(self.target_cost)))
        print("entry cost is {t}".format(t=market.quote.print(self.entry_cost)))
        print("exit cost is {t}".format(t=market.quote.print(self.exit_cost)))

        self.sync_limit_orders()

        self.check_stops(last_p)

        # check if position has to be closed
        if self.entry_cost > 0 and self.is_open() and signal == SELL:
            self.close()

        if self.is_pending():
            self.refresh_bucket(last_p)

        self.refresh_status()

        self.postpone()

        self.save()

    def refresh_bucket(self, last_p):
        strategy = self.user_strategy.strategy
        market = strategy.market
        now = datetime.datetime.utcnow()

        if self.stopped:
            engine = strategy.stop_engine
        elif self.is_open():
            engine = strategy.buy_engine
        else:
            engine = strategy.sell_engine

        print("next bucket at {t}".format(t=self.next_bucket))

        # check if current bucket needs to be reset
        if now > self.next_bucket:
            next_bucket = get_next_refresh(engine.bucket_interval)
            self.next_bucket = next_bucket
            print("moving on to next bucket at {b}".format(b=self.next_bucket))
            self.bucket = 0

        print("limit to market ratio is {r}".format(r=engine.lm_ratio))

        if self.status == "opening":
            remaining_cost = self.get_remaining_cost()
            remaining_amount = market.base.div(
                remaining_cost, last_p, prec=market.amount_precision
            )

            m_total_cost = int(engine.lm_ratio * remaining_cost)
            m_total_amount = market.base.div(
                m_total_cost, last_p, prec=market.amount_precision
            )

            # slippage
            m_total_amount *= 0.99

        elif self.status == "closing":
            remaining_amount = self.get_remaining_amount(last_p)
            remaining_cost = market.base.format(remaining_amount) * last_p

            m_total_amount = int(engine.lm_ratio * remaining_amount)

        # check if current bucket is filled
        if now < self.next_bucket and remaining_cost < market.cost_min:
            print("bucket is full")
            return

        inserted_orders = False

        if self.status == "opening":
            side = "buy"

            if m_total_amount > 0:
                inserted_orders = self.exchange.create_order(
                    self, "market", side, m_total_amount, last_p
                )

            if engine.lm_ratio < 1:
                l_total = self.get_remaining_cost()
                if l_total > 0:
                    inserted_orders = self.exchange.create_limit_buy_orders(
                        self, l_total, last_p, engine.num_orders, engine.spread
                    )

        elif self.status == "closing":
            side = "sell"

            if m_total_amount > 0:
                inserted_orders = self.exchange.create_order(
                    self, "market", side, m_total_amount, last_p
                )

            if engine.lm_ratio < 1:
                l_total = self.get_remaining_amount(last_p)
                if l_total > 0:
                    inserted_orders = self.exchange.create_limit_sell_orders(
                        self, l_total, last_p, engine.num_orders, engine.spread
                    )

        # if bucket is not full but can't insert new orders, fill at market
        if not inserted_orders:
            inserted_orders = self.exchange.create_order(
                self, "market", side, remaining_amount, last_p
            )

        if not inserted_orders:
            self.user_strategy.user.send_message(
                self.get_notice(prefix="could not insert any orders for ")
            )

    def refresh_status(self):
        strategy = self.user_strategy.strategy
        market = strategy.market
        user = self.user_strategy.user

        # position finishes closing when exit equals entry
        amount_diff = self.entry_amount - self.exit_amount
        cost_diff = int(market.quote.format(amount_diff * self.exit_price))
        if (
            self.exit_cost > 0
            and self.status == "closing"
            and cost_diff < market.cost_min
        ):
            self.status = "closed"
            self.pnl = self.exit_cost - self.entry_cost - self.fee
            self.roi = get_roi(self.entry_cost, self.pnl)
            self.exit_time = datetime.datetime.utcnow()
            print(
                "position is now closed, pnl: {r}".format(
                    r=market.quote.print(self.pnl)
                )
            )
            user.send_message(
                self.get_notice(
                    prefix="closed ", suffix=" ROI: {r}%".format(r=self.roi)
                )
            )

        # position finishes opening when it reaches target
        cost_diff = self.target_cost - self.entry_cost
        if (
            self.status == "opening"
            and self.entry_cost > 0
            and cost_diff < market.cost_min
        ):
            self.status = "open"
            print("position is now open")
            user.send_message(self.get_notice(prefix="opened "))

        # handle special case of hanging position
        signal = self.user_strategy.strategy.get_signal()
        SELL = StrategySignals.SELL
        if self.entry_cost == 0 and (self.status == "closing" or signal == SELL):
            print("entry_cost is 0, position is now closed")
            self.status = "closed"
            self.exit_time = datetime.datetime.utcnow()

        self.save()
