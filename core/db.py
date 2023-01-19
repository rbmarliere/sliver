import datetime
from decimal import Decimal as D

import peewee
from ccxt.base.decimal_to_precision import DECIMAL_PLACES, NO_PADDING

import core
from core.watchdog import info as i, notice as n


# precision modes:
# DECIMAL_PLACES,
# SIGNIFICANT_DIGITS,
# TICK_SIZE,

# padding modes:
# NO_PADDING,
# PAD_WITH_ZERO,

connection = peewee.PostgresqlDatabase(
    core.config["DB_NAME"], **{
        "host": core.config["DB_HOST"],
        "user": core.config["DB_USER"],
        "password": core.config["DB_PASSWORD"]
    })


class BaseModel(peewee.Model):

    class Meta:
        database = connection


class Asset(BaseModel):
    ticker = peewee.TextField(unique=True)


class Exchange(BaseModel):
    name = peewee.TextField(unique=True)
    rate_limit = peewee.IntegerField(default=1200)
    precision_mode = peewee.IntegerField(default=DECIMAL_PLACES)
    padding_mode = peewee.IntegerField(default=NO_PADDING)
    timeframes = peewee.TextField(null=True)


class User(BaseModel):
    email = peewee.TextField(unique=True)
    password = peewee.TextField()
    access_key = peewee.TextField(unique=True, null=True)
    max_risk = peewee.DecimalField(default=0.1)
    cash_reserve = peewee.DecimalField(default=0.25)
    telegram_username = peewee.TextField(null=True)
    telegram_chat_id = peewee.TextField(null=True)

    def get_exchange_credential(self, exchange: Exchange):
        return self \
            .credential_set \
            .where(Credential.exchange == exchange)

    def get_active_credential(self, exchange: Exchange):
        return self.get_exchange_credential(exchange) \
            .where(Credential.active)

    def get_balances_by_asset(self, asset: Asset):
        return Balance \
            .select() \
            .join(ExchangeAsset,
                  on=(Balance.asset_id == ExchangeAsset.id)) \
            .join(Asset) \
            .switch(Balance) \
            .join(User) \
            .where(Balance.user_id == self.id) \
            .where(Asset.id == asset.id) \
            .order_by(Asset.ticker)

    def get_open_positions(self):
        return get_open_positions() \
            .where(UserStrategy.user_id == self.id)

    def get_exchange_open_positions(self, exchange: Exchange):
        return self.get_open_positions() \
            .join(Market) \
            .join(ExchangeAsset,
                  on=(Market.base_id == ExchangeAsset.id)) \
            .join(Exchange) \
            .where(Exchange.id == exchange.id)

    def get_exchange_strategies(self, exchange: Exchange):
        return self.userstrategy_set \
            .join(Strategy) \
            .join(Market) \
            .join(ExchangeAsset,
                  on=(Market.base_id == ExchangeAsset.id)) \
            .join(Exchange) \
            .where(Exchange.id == exchange.id) \
            .where(UserStrategy.user_id == self.id) \
            .where(UserStrategy.active) \
            .where(Strategy.active)

    def get_positions(self):
        return Position \
            .select(Position,
                    Strategy.id.alias("strategy_id"),
                    Market.id.alias("market_id")) \
            .join(UserStrategy) \
            .join(Strategy) \
            .join(Market) \
            .where(UserStrategy.user_id == self.id) \
            .order_by(Position.id.desc())

    def is_subscribed(self, strategy_id):
        for u_st in self.userstrategy_set:
            if u_st.strategy_id == strategy_id:
                return u_st.active
        return False


class Credential(BaseModel):
    user = peewee.ForeignKeyField(User)
    exchange = peewee.ForeignKeyField(Exchange)
    api_key = peewee.TextField()
    api_secret = peewee.TextField()
    active = peewee.BooleanField(default=True)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, exchange_id)")]

    def disable(self):
        i("disabling credential {s}...".format(s=self))
        self.active = False
        self.save()


class ExchangeAsset(BaseModel):
    exchange = peewee.ForeignKeyField(Exchange)
    asset = peewee.ForeignKeyField(Asset)
    precision = peewee.IntegerField(default=1)

    def div(self, num, den, prec=None):
        if prec is None:
            prec = self.precision

        div = int(D(str(num)) / D(str(den)) * 10**prec)

        if prec == self.precision:
            return div
        else:
            return self.transform(div, prec=(self.precision - prec))

    def format(self, value, prec=None):
        if not value:
            return 0
        if prec is None:
            prec = self.precision
        precision = D("10") ** D(str(-1 * self.precision))
        value = D(str(value)) * precision
        if prec == self.precision:
            return value.quantize(precision)
        else:
            trunc_precision = D("10") ** D(str(-1 * prec))
            return value.quantize(trunc_precision)

    def transform(self, value, prec=None):
        if not value:
            return 0
        if prec is None:
            prec = self.precision
        precision = D("10") ** D(str(prec))
        return int(D(str(value)) * precision)

    def print(self, value):
        value = self.format(value)
        return "{n:.{p}f} {t}".format(n=value,
                                      p=self.precision,
                                      t=self.asset.ticker)


class Balance(BaseModel):
    user = peewee.ForeignKeyField(User)
    asset = peewee.ForeignKeyField(ExchangeAsset)
    value_asset = peewee.ForeignKeyField(ExchangeAsset)
    free = peewee.BigIntegerField(null=True)
    used = peewee.BigIntegerField(null=True)
    total = peewee.BigIntegerField(null=True)
    free_value = peewee.BigIntegerField(null=True)
    used_value = peewee.BigIntegerField(null=True)
    total_value = peewee.BigIntegerField(null=True)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (asset_id, user_id)")]


class Market(BaseModel):
    base = peewee.ForeignKeyField(ExchangeAsset)
    quote = peewee.ForeignKeyField(ExchangeAsset)
    amount_precision = peewee.IntegerField(null=True)
    price_precision = peewee.IntegerField(null=True)
    amount_min = peewee.BigIntegerField(null=True)
    cost_min = peewee.BigIntegerField(null=True)
    price_min = peewee.BigIntegerField(null=True)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (base_id, quote_id)")]

    def get_symbol(self):
        return self.base.asset.ticker + "/" + self.quote.asset.ticker


class Strategy(BaseModel):
    creator = peewee.ForeignKeyField(User)
    description = peewee.TextField()
    type = peewee.IntegerField(default=0)
    active = peewee.BooleanField(default=False)
    deleted = peewee.BooleanField(default=False)
    market = peewee.ForeignKeyField(Market)
    timeframe = peewee.TextField(default="1d")
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    orders_interval = peewee.IntegerField(default=1)  # 1 minute
    num_orders = peewee.IntegerField(default=1)
    bucket_interval = peewee.IntegerField(default=60)  # 1 hour
    min_buckets = peewee.IntegerField(default=1)
    spread = peewee.DecimalField(default=1)  # 1%
    stop_gain = peewee.DecimalField(default=5)  # 5%
    trailing_gain = peewee.BooleanField(default=False)
    stop_loss = peewee.DecimalField(default=3)  # -3%
    trailing_loss = peewee.BooleanField(default=False)
    lm_ratio = peewee.DecimalField(default=0)

    def get_signal(self):
        return core.strategies.load(self).get_signal()

    def refresh(self):
        symbol = self.market.get_symbol()

        i("===========================================")
        i("refreshing strategy {s}".format(s=self))
        i("market is {m} ({i})".format(m=symbol, i=self.market.id))
        i("timeframe is {T}".format(T=self.timeframe))
        i("exchange is {e}".format(e=self.market.base.exchange.name))
        i("type is {m}".format(m=core.strategies.Types(self.type).name))

        # ideas:
        # - reset num_orders, spread and refresh_interval dynamically
        # - base decision over price data and inventory
        #   (amount opened, risk, etc)

        # download historical price ohlcv data
        core.exchange.download_prices(self)

        core.strategies.load(self).refresh()

        i("signal is {s}".format(s=self.get_signal()))

        self.postpone()

    def disable(self):
        i("disabling strategy {s}...".format(s=self))
        self.active = False
        self.save()

    def delete(self):
        self.deleted = True
        self.active = False
        self.save()

    def postpone(self):
        interval = core.utils.get_timeframe_in_seconds(self.timeframe) / 60
        self.next_refresh = core.utils.get_next_refresh(interval)
        i("next refresh at {n}".format(n=self.next_refresh))
        self.save()

    def subscribe(self, user, subscribed):
        if subscribed is None:
            subscribed = False

        # user can only subscribe to one strategy per market
        if subscribed:
            for u_st in user.userstrategy_set:
                if u_st.strategy.market == self.market \
                        and u_st.strategy != self \
                        and u_st.active:
                    raise core.errors.MarketAlreadySubscribed

        user_strat_exists = False
        for u_st in user.userstrategy_set:
            if u_st.strategy_id == self.id:
                user_strat_exists = True
                u_st.active = subscribed
                u_st.save()

        if not user_strat_exists:
            core.db.UserStrategy(user=user,
                                 strategy=self,
                                 active=subscribed).save()

    def get_active_users(self):
        return UserStrategy \
            .select() \
            .join(Strategy) \
            .where((Strategy.id == self.id) & (UserStrategy.active))

    def get_prices(self):
        return Price \
            .select() \
            .where((Price.market == self.market)
                   & (Price.timeframe == self.timeframe)) \
            .order_by(Price.time)


class UserStrategy(BaseModel):
    user = peewee.ForeignKeyField(User)
    strategy = peewee.ForeignKeyField(Strategy)
    active = peewee.BooleanField(default=False)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, strategy_id)")]

    def disable(self):
        i("disabling user's strategy {s}...".format(s=self))
        self.active = False
        self.save()

    def get_active_position_or_none(self):
        return get_open_positions() \
            .where(UserStrategy.user_id == self.user_id) \
            .where(UserStrategy.strategy_id == self.strategy_id) \
            .get_or_none()

    def refresh(self):
        strategy = self.strategy

        i("...........................................")
        i("refreshing user {u} strategy {s}".format(u=self.user, s=self))

        # sync orders of active position
        position = self.get_active_position_or_none()

        if position is None:
            if strategy.get_signal() == "buy":
                t_cost = core.inventory.get_target_cost(self)

                if (t_cost == 0 or t_cost < strategy.market.cost_min):
                    i("invalid target_cost, could not create position")

                if t_cost > 0:
                    position = core.db.Position.open(self, t_cost)

        elif position.is_open() and strategy.get_signal() == "sell":
            position.next_refresh = datetime.datetime.utcnow()
            position.save()


class Position(BaseModel):
    user_strategy = peewee.ForeignKeyField(UserStrategy)
    # based on user_strategy.strategy.orders_interval
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    # time limit on each buy/sell step for DCA
    next_bucket = peewee.DateTimeField(default=datetime.datetime.utcnow())
    # maximum cost|amount for any time period
    bucket_max = peewee.BigIntegerField()
    # effective cost|amount for current period
    bucket = peewee.BigIntegerField(default=0)
    # status of the position, e.g. open | close
    status = peewee.TextField()
    # desired position size in quote
    target_cost = peewee.BigIntegerField()
    # total effective cost paid in quote
    entry_cost = peewee.BigIntegerField(default=0)
    # total amount in base
    entry_amount = peewee.BigIntegerField(default=0)
    # average prices in quote
    entry_price = peewee.BigIntegerField(default=0)
    exit_price = peewee.BigIntegerField(default=0)
    exit_amount = peewee.BigIntegerField(default=0)
    exit_cost = peewee.BigIntegerField(default=0)
    # total fees in quote
    fee = peewee.BigIntegerField(default=0)
    # position profit or loss
    pnl = peewee.BigIntegerField(default=0)
    roi = peewee.FloatField(default=0)
    # peak prices for trailing stop calc.
    last_high = peewee.BigIntegerField(default=0)
    last_low = peewee.BigIntegerField(default=0)

    def get_notice(self, prefix="", suffix=""):
        return ("{p}position of strategy {s} in market {m} {su}"
                .format(p=prefix,
                        s=self.user_strategy.strategy,
                        m=self.user_strategy.strategy.market.get_symbol(),
                        su=suffix))

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
        return Order \
            .select(Order, Strategy.id.alias("strategy_id")) \
            .join(Position) \
            .join(UserStrategy) \
            .join(Strategy) \
            .where((Order.status != "canceled") | (Order.filled > 0)) \
            .where(Position.id == self.id) \
            .order_by(Order.time.desc())

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

        balance = core.inventory \
            .get_balance_by_exchange_asset(user=self.user_strategy.user,
                                           asset=market.quote)
        remaining = min(remaining, balance.total)

        i("bucket cost is {a}".format(a=market.quote.print(self.bucket)))
        i("remaining to fill in bucket is {r}"
            .format(r=market.quote.print(remaining)))
        i("balance is {r}".format(r=market.quote.print(balance.total)))

        return remaining

    def get_remaining_amount(self, last_price):
        market = self.user_strategy.strategy.market

        remaining_to_fill = self.get_remaining_to_fill()
        remaining_to_exit = self.get_remaining_to_exit()
        remaining = min(abs(remaining_to_fill), abs(remaining_to_exit))

        balance = core.inventory \
            .get_balance_by_exchange_asset(user=self.user_strategy.user,
                                           asset=market.base)
        remaining = min(remaining, balance.total)

        i("bucket amount is {a}".format(a=market.base.print(self.bucket)))
        i("remaining to fill in bucket is {r}"
            .format(r=market.base.print(remaining_to_fill)))
        i("remaining to exit position is {r}"
            .format(r=market.base.print(remaining_to_exit)))
        i("balance is {r}".format(r=market.base.print(balance.total)))

        # avoid position rounding errors by exiting early
        r = remaining_to_exit - remaining_to_fill
        position_remainder = market.base.format(r)
        if position_remainder > 0 \
                and position_remainder * last_price <= market.cost_min:
            i("position remainder is {r}".format(r=market.base.print(r)))
            remaining = remaining_to_exit

        return remaining

    def open(u_st: UserStrategy, t_cost: int):
        strategy = u_st.strategy
        market = strategy.market
        user = u_st.user

        next_bucket = core.utils.get_next_refresh(strategy.bucket_interval)

        bucket_max = \
            market.quote.div(t_cost,
                             market.quote.transform(strategy.min_buckets),
                             prec=strategy.market.price_precision)

        position = Position(user_strategy=u_st,
                            next_bucket=next_bucket,
                            bucket_max=bucket_max,
                            status="opening",
                            target_cost=t_cost)
        position.save()

        i("opening position {i}".format(i=position.id))
        n(user, position.get_notice(prefix="opening "))

        return position

    def close(self):
        strategy = self.user_strategy.strategy
        market = strategy.market
        user = self.user_strategy.user

        self.bucket_max = \
            market.base.div(self.entry_amount,
                            market.base.transform(strategy.min_buckets),
                            prec=strategy.market.amount_precision)
        self.bucket = 0
        self.status = "closing"

        i("closing position {i}".format(i=self.id))
        n(user, self.get_notice(prefix="closing "))

        self.save()

    def postpone(self):
        interval = self.user_strategy.strategy.orders_interval
        self.next_refresh = core.utils.get_next_refresh(interval)
        i("next refresh at {n}".format(n=self.next_refresh))
        self.save()

    def check_stops(self, last_price=None):
        if not self.is_open():
            return False

        strategy = self.user_strategy.strategy
        market = strategy.market
        user = self.user_strategy.user

        if strategy.stop_loss <= 0 or strategy.stop_gain <= 0:
            return False

        if self.entry_price == 0:
            return False

        if last_price is None:
            core.exchange.set_api(exchange=market.base.exchange)
            p = core.exchange.api.fetch_ticker(market.get_symbol())
            last_price = market.quote.transform(p["last"])

        if last_price > self.last_high:
            self.last_high = last_price
            self.save()
        if last_price < self.last_low or self.last_low == 0:
            self.last_low = last_price
            self.save()

        curr_gain = 0
        curr_loss = 0

        if strategy.trailing_gain:
            # multiply by -1 because when taken from the high, it is negative
            # if price is lower than entry, there are no gains to stop
            if last_price > self.entry_price:
                curr_gain = core.utils.get_roi(self.last_high, last_price) * -1
        else:
            curr_gain = core.utils.get_roi(self.entry_price, last_price)

        if strategy.trailing_loss:
            # if price is higher than entry, there are no losses to stop
            if last_price < self.entry_price:
                curr_loss = core.utils.get_roi(self.last_low, last_price)
        else:
            # multiply by -1 because strategy.stop_loss is stored as positive
            curr_loss = core.utils.get_roi(self.entry_price, last_price) * -1

        if curr_gain > strategy.stop_gain or curr_loss > strategy.stop_loss:
            i("last price is {p}, high was {h} and low was {l}"
              .format(p=market.quote.print(last_price),
                      h=market.quote.print(self.last_high),
                      l=market.quote.print(self.last_low)))
            i("stop gain is {g}, trailing is {gt}"
              .format(g=strategy.stop_gain,
                      gt=strategy.trailing_gain))
            i("stop loss is {l}, trailing is {lt}"
              .format(l=strategy.stop_loss,
                      lt=strategy.trailing_loss))
            n(user, self.get_notice(prefix="stopped "))
            self.close()
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
                self.entry_price = \
                    market.quote.div(self.entry_cost, self.entry_amount)

        elif order.side == "sell":
            self.bucket += order.filled
            self.exit_amount += order.filled
            self.exit_cost += order.cost
            self.fee += order.fee

            if self.exit_amount > 0:
                self.exit_price = \
                    market.quote.div(self.exit_cost, self.exit_amount)

        self.save()

    def refresh(self):
        strategy = self.user_strategy.strategy
        signal = strategy.get_signal()
        market = strategy.market

        core.exchange.set_api(exchange=market.base.exchange)
        p = core.exchange.api.fetch_ticker(market.get_symbol())
        last_p = market.quote.transform(p["last"])

        i("___________________________________________")
        i("refreshing {s} position {i}".format(s=self.status, i=self.id))
        i("strategy is {s}".format(s=self.user_strategy.strategy.id))
        i("last price is {p}".format(p=strategy.market.quote.print(last_p)))
        i("target cost is {t}".format(t=market.quote.print(self.target_cost)))
        i("entry cost is {t}".format(t=market.quote.print(self.entry_cost)))
        i("exit cost is {t}".format(t=market.quote.print(self.exit_cost)))

        self.check_stops(last_p)

        # check if position has to be closed
        if self.entry_cost > 0 and self.is_open() and signal == "sell":
            self.close()

        # handle special case of hanging position
        if self.entry_cost == 0 \
                and (self.status == "closing" or signal == "sell"):
            i("entry_cost is 0, position is now closed")
            self.status = "closed"

        if self.is_pending():
            market_total, limit_total = self.refresh_bucket(last_p)
            self.refresh_orders(market_total, limit_total, last_p)

        self.refresh_status()

        self.postpone()

        self.save()

    def refresh_bucket(self, last_p):
        strategy = self.user_strategy.strategy
        market = strategy.market
        now = datetime.datetime.utcnow()

        i("next bucket at {t}".format(t=self.next_bucket))

        # check if current bucket needs to be reset
        if now > self.next_bucket:
            next_bucket = core.utils.get_next_refresh(strategy.bucket_interval)
            self.next_bucket = next_bucket
            i("moving on to next bucket at {b}".format(b=self.next_bucket))
            self.bucket = 0

        core.exchange.sync_limit_orders(self)

        i("limit to market ratio is {r}".format(r=strategy.lm_ratio))

        if self.status == "opening":
            remaining_cost = self.get_remaining_cost()
            remaining_amount = \
                market.base.div(remaining_cost,
                                last_p,
                                prec=market.amount_precision)

            m_total_cost = int(strategy.lm_ratio * remaining_cost)
            l_total_cost = remaining_cost - m_total_cost

            m_total_amount = \
                market.base.div(m_total_cost,
                                last_p,
                                prec=market.amount_precision)
            l_total = l_total_cost

        elif self.status == "closing":
            remaining_amount = self.get_remaining_amount(last_p)
            remaining_cost = market.base.format(remaining_amount) * last_p

            m_total_cost = int(strategy.lm_ratio * remaining_cost)
            l_total_cost = remaining_cost - m_total_cost

            m_total_amount = int(strategy.lm_ratio * remaining_amount)
            l_total = remaining_amount - m_total_amount

        # check if current bucket is filled
        if now < self.next_bucket and remaining_cost < market.cost_min:
            i("bucket is full")
            return 0, 0

        # if bucket is not full but can't insert new orders, fill at market
        if m_total_cost < market.cost_min and l_total_cost < market.cost_min:
            return remaining_amount, 0

        return m_total_amount, l_total

    def refresh_orders(self, market_total, limit_total, last_p):
        strategy = self.user_strategy.strategy

        if self.status == "opening":
            if market_total > 0:
                core.exchange.create_order("market",
                                           "buy",
                                           self,
                                           market_total,
                                           last_p)

            if limit_total > 0:
                core.exchange.create_limit_buy_orders(limit_total,
                                                      self,
                                                      last_p,
                                                      strategy.num_orders,
                                                      strategy.spread)

        elif self.status == "closing":
            if market_total > 0:
                core.exchange.create_order("market",
                                           "sell",
                                           self,
                                           market_total,
                                           last_p)

            if limit_total > 0:
                core.exchange.create_limit_sell_orders(limit_total,
                                                       self,
                                                       last_p,
                                                       strategy.num_orders,
                                                       strategy.spread)

    def refresh_status(self):
        strategy = self.user_strategy.strategy
        market = strategy.market
        user = self.user_strategy.user

        # position finishes closing when exit equals entry
        amount_diff = self.entry_amount - self.exit_amount
        cost_diff = int(market.quote.format(amount_diff * self.exit_price))
        if self.exit_cost > 0 \
                and self.status == "closing" \
                and cost_diff < market.cost_min:
            self.status = "closed"
            self.pnl = (self.exit_cost
                        - self.entry_cost
                        - self.fee)
            self.roi = core.utils.get_roi(self.entry_price, self.exit_price)
            i("position is now closed, pnl: {r}"
              .format(r=market.quote.print(self.pnl)))
            n(user, self.get_notice(prefix="closed ",
                                    suffix=" ROI: {r}%"
                                    .format(r=self.roi)))

        # position finishes opening when it reaches target
        cost_diff = self.target_cost - self.entry_cost
        if self.status == "opening" \
                and self.entry_cost > 0 \
                and cost_diff < market.cost_min:
            self.status = "open"
            i("position is now open")
            n(user, self.get_notice(suffix="is now open"))


class Order(BaseModel):
    # which position it belongs to
    position = peewee.ForeignKeyField(Position)
    # id comes from exchange api
    exchange_order_id = peewee.TextField()
    # datetime of the order
    time = peewee.DateTimeField()
    # can be open, canceled, closed
    status = peewee.TextField()
    # can be limit, market, etc
    type = peewee.TextField()
    # can be buy or sell
    side = peewee.TextField()
    # order price in quote, if market then average
    price = peewee.BigIntegerField()
    # total order size in base
    amount = peewee.BigIntegerField()
    # effective order cost in quote
    cost = peewee.BigIntegerField()
    # effective amount filled in base
    filled = peewee.BigIntegerField()
    # effective fee paid
    fee = peewee.BigIntegerField()

    def sync(self, ex_order, position):
        market = position.user_strategy.strategy.market

        id = ex_order["id"]
        status = ex_order["status"]
        type = ex_order["type"]
        side = ex_order["side"]
        time = ex_order["datetime"]
        if not time:
            time = datetime.datetime.utcnow()

        price = ex_order["average"]
        amount = ex_order["amount"]
        filled = ex_order["filled"]
        if not filled:
            filled = 0
        cost = ex_order["cost"]
        if not cost:
            cost = filled * amount

        # transform values to db entry standard
        price = market.quote.transform(price)
        amount = market.base.transform(amount)
        cost = market.quote.transform(cost)
        filled = market.base.transform(filled)

        implicit_cost = market.base.format(amount)*price
        i("{a} @ {p} ({c})".format(a=market.base.print(amount),
                                   p=market.quote.print(price),
                                   c=market.quote.print(implicit_cost)))

        i("filled: {f}".format(f=market.base.print(filled)))

        # check for fees
        if ex_order["fee"] is None:
            # TODO maybe fetch from difference between insertion & filled
            fee = 0
        else:
            try:
                fee = market.quote.transform(ex_order["fee"]["cost"])
            except KeyError:
                fee = 0

        if not status:
            if self.id:
                if filled == cost:
                    status = "closed"
                else:
                    status = "canceled"
            else:
                status = "open"

        self.position = position
        self.exchange_order_id = id
        self.time = time
        self.status = status
        self.type = type
        self.side = side
        self.price = price
        self.amount = amount
        self.cost = cost
        self.filled = filled
        self.fee = fee

        self.save()

        if status != "open":
            position.add_order(self)


class Price(BaseModel):
    market = peewee.ForeignKeyField(Market)
    timeframe = peewee.TextField()
    time = peewee.DateTimeField()
    open = peewee.BigIntegerField()
    high = peewee.BigIntegerField()
    low = peewee.BigIntegerField()
    close = peewee.BigIntegerField()
    volume = peewee.BigIntegerField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (market_id, timeframe, time)")]


class Indicator(BaseModel):
    strategy = peewee.ForeignKeyField(Strategy)
    price = peewee.ForeignKeyField(Price)
    signal = peewee.TextField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (price_id, strategy_id)")]


def get_active_positions():
    return Position.select() \
        .join(UserStrategy) \
        .join(Strategy) \
        .where(Strategy.active) \
        .where(UserStrategy.active)


def get_opening_positions():
    return get_active_positions() \
        .where(Position.status << ["open", "opening"])


def get_open_positions():
    return get_active_positions() \
        .where(Position.status << ["open", "opening", "closing"])


def get_pending_positions():
    return get_open_positions() \
        .where(Position.next_refresh < datetime.datetime.utcnow())


def get_pending_strategies():
    return Strategy \
        .select() \
        .where(Strategy.active) \
        .where(Strategy.next_refresh < datetime.datetime.utcnow()) \
        .order_by(Strategy.next_refresh)
