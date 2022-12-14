import datetime
from decimal import Decimal as D

import pandas
import peewee
from ccxt.base.decimal_to_precision import DECIMAL_PLACES, NO_PADDING

import core

# precision modes:
# DECIMAL_PLACES,
# SIGNIFICANT_DIGITS,
# TICK_SIZE,

# padding modes:
# NO_PADDING,
# PAD_WITH_ZERO,

connection = peewee.PostgresqlDatabase(
    core.config["HYPNOX_DB_NAME"], **{
        "host": core.config["HYPNOX_DB_HOST"],
        "user": core.config["HYPNOX_DB_USER"],
        "password": core.config["HYPNOX_DB_PASSWORD"]
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
    telegram = peewee.TextField(null=True)
    max_risk = peewee.DecimalField(default=0.1)
    cash_reserve = peewee.DecimalField(default=0.25)
    target_factor = peewee.DecimalField(default=0.1)

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
        return Position \
            .select() \
            .join(UserStrategy) \
            .where(
                (UserStrategy.user_id == self.id)
                & ((Position.status == "open")
                    | (Position.status == "opening")
                    | (Position.status == "closing")))

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

    def is_subscribed(self, strategy):
        for u_st in self.userstrategy_set:
            if u_st.strategy == strategy:
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


class ExchangeAsset(BaseModel):
    exchange = peewee.ForeignKeyField(Exchange)
    asset = peewee.ForeignKeyField(Asset)
    precision = peewee.IntegerField(default=1)

    def div(self, num, den, trunc_precision=None):
        if not trunc_precision:
            trunc_precision = self.precision

        div = D(str(num)) / D(str(den))

        if abs(num) > abs(den):
            div = int(div)
        else:
            div = self.transform(div)

        div = core.utils.truncate(self.format(div), trunc_precision)

        return self.transform(div)

    def format(self, value):
        precision = D("10") ** D(-1 * self.precision)
        value = D(str(value)) * precision
        return value.quantize(precision)

    def transform(self, value):
        precision = D(10) ** D(self.precision)
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
    user = peewee.ForeignKeyField(User)
    market = peewee.ForeignKeyField(Market)
    active = peewee.BooleanField(default=False)
    description = peewee.TextField()
    mode = peewee.TextField(default="auto")
    timeframe = peewee.TextField(default="1d")
    signal = peewee.TextField(default="neutral")
    refresh_interval = peewee.IntegerField(default=1)  # 1 minute
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    num_orders = peewee.IntegerField(default=1)
    bucket_interval = peewee.IntegerField(default=60)  # 1 hour
    spread = peewee.DecimalField(default=1)  # 1%
    min_roi = peewee.DecimalField(default=5)  # 5%
    stop_loss = peewee.DecimalField(default=3)  # -3%
    i_threshold = peewee.DecimalField(default=0)
    p_threshold = peewee.DecimalField(default=0)
    tweet_filter = peewee.TextField(default="")
    lm_ratio = peewee.DecimalField(default=0)
    model_i = peewee.TextField(null=True)
    model_p = peewee.TextField(null=True)

    def disable(self):
        core.watchdog.info("disabling strategy {s}...".format(s=self))
        self.active = False
        self.save()

    def postpone(self):
        core.watchdog.info("next refresh at {n}".format(n=self.next_refresh))
        self.next_refresh = self.get_next_refresh()
        self.save()

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

    def get_indicators(self):
        return self.get_prices() \
            .select(Price, Indicator) \
            .join(Indicator,
                  peewee.JOIN.LEFT_OUTER,
                  on=((Indicator.price_id == Price.id)
                      & (Indicator.strategy == self)))

    def get_rsignal(self):
        import random
        r = random.randint(1, 10)
        if r >= 8:
            return "buy"
        elif r <= 2:
            return "sell"
        else:
            return "neutral"

    def get_asignal(self):
        indicators = pandas.DataFrame(self.get_indicators().dicts())
        if indicators.empty:
            return "neutral"
        signal = indicators.iloc[-1].signal
        if signal is None:
            return "neutral"
        return signal

    def get_next_refresh(self):
        freq = "{i}T".format(i=self.refresh_interval)
        now = datetime.datetime.utcnow()
        last = now.replace(minute=0, second=0, microsecond=0)
        range = pandas.date_range(last, periods=61, freq=freq)
        series = range.to_series().asfreq(freq)
        next_refresh = series.loc[series > now].iloc[0]
        return next_refresh


class UserStrategy(BaseModel):
    user = peewee.ForeignKeyField(User)
    strategy = peewee.ForeignKeyField(Strategy)
    active = peewee.BooleanField(default=False)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, strategy_id)")]

    def disable(self):
        core.watchdog.info("disabling user's strategy {s}...".format(s=self))
        self.active = False
        self.save()

    def get_active_position_or_none(self):
        return Position \
            .select() \
            .join(UserStrategy) \
            .join(Strategy) \
            .join(Market) \
            .where(UserStrategy.user_id == self.user_id) \
            .where(UserStrategy.strategy_id == self.strategy_id) \
            .where((Position.status == "open")
                   | (Position.status == "opening")
                   | (Position.status == "closing")) \
            .get_or_none()


class Position(BaseModel):
    user_strategy = peewee.ForeignKeyField(UserStrategy)
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

    def open(u_st: UserStrategy, tcost: int):
        strategy = u_st.strategy
        now = datetime.datetime.utcnow()
        next_bucket = now + datetime.timedelta(
            minutes=strategy.bucket_interval)

        bucket_max = strategy.market.quote.div(
            tcost,
            strategy.num_orders,
            trunc_precision=strategy.market.price_precision)

        position = Position(user_strategy=u_st,
                            next_bucket=next_bucket,
                            bucket_max=bucket_max,
                            status="opening",
                            target_cost=tcost)
        position.save()

        core.watchdog.info("opening position {i}".format(i=position.id))
        core.watchdog.notice("opening " + position.get_notice())

        return position

    def get_notice(self):
        return ("position for user {u} under strategy {s} in market {m}"
                .format(
                    u=self.user_strategy.user.email,
                    s=self.user_strategy.strategy,
                    m=self.user_strategy.strategy.market.get_symbol()))

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
        return self.status != "closing" and self.status != "closed"

    def is_pending(self):
        return self.status == "opening" or self.status == "closing"

    def get_remaining_to_fill(self):
        return self.bucket_max - self.bucket

    def get_remaining_to_exit(self):
        return self.entry_amount - self.exit_amount

    def get_remaining_to_open(self):
        return min(self.target_cost - self.entry_cost,
                   self.bucket_max - self.bucket)

    def get_remaining(self, last_price):
        market = self.user_strategy.strategy.market

        if self.status == "opening":
            # remaining is a cost
            remaining = self.get_remaining_to_open()

            core.watchdog.info(
                "bucket cost is {a}"
                .format(a=market.quote.print(self.bucket)))
            core.watchdog.info(
                "remaining to fill in bucket is {r}"
                .format(r=market.quote.print(remaining)))

            return remaining

        elif self.status == "closing":
            # remaining is an amount
            remaining_to_fill = self.get_remaining_to_fill()
            remaining_to_exit = self.get_remaining_to_exit()
            remaining = min(remaining_to_fill, remaining_to_exit)
            core.watchdog.info(
                "bucket amount is {a}"
                .format(a=market.base.print(self.bucket)))
            core.watchdog.info(
                "remaining to fill in bucket is {r}"
                .format(r=market.base.print(remaining_to_fill)))
            core.watchdog.info(
                "remaining to exit position is {r}"
                .format(r=market.base.print(remaining_to_exit)))

            # avoid position rounding errors by exiting early
            r = remaining_to_exit - remaining_to_fill
            position_remainder = market.base.format(r)
            if (position_remainder > 0
                    and
                    position_remainder * last_price <= market.cost_min):
                core.watchdog.info("position remainder is {r}"
                                   .format(r=market.base.print(r)))
                remaining = remaining_to_exit

            return remaining

    def add_order(self, order):
        market = self.user_strategy.strategy.market

        # update self info
        if order.side == "buy":
            self.bucket += order.cost
            self.entry_cost += order.cost
            self.entry_amount += order.filled
            self.fee += order.fee

            # update entry price if entry_amount is non zero
            if self.entry_amount > 0:
                self.entry_price = market.quote.transform(
                    (self.entry_cost / self.entry_amount))

        elif order.side == "sell":
            self.bucket += order.filled
            self.exit_amount += order.filled
            self.exit_cost += order.cost
            self.fee += order.fee

            # update exit price if exit_amount is non zero
            if self.exit_amount > 0:
                self.exit_price = market.quote.transform(
                    (self.exit_cost / self.exit_amount))

        self.save()


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
            time = datetime.datetime.now()

        price = ex_order["price"]
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
        filled = market.quote.transform(filled)

        msg = "{a} @ {p} ({c})" \
            .format(a=market.base.print(amount),
                    p=market.quote.print(price),
                    c=market.quote.print(market.base.format(amount)*price))

        core.watchdog.info(msg)

        if self.id:
            core.watchdog.info("filled: {f}"
                               .format(f=market.quote.print(filled)))
            if filled > 0:
                core.watchdog.notice(msg)

        # check for fees
        if ex_order["fee"] is None:
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
    i_score = peewee.DecimalField()
    i_mean = peewee.DecimalField()
    i_variance = peewee.DecimalField()
    p_score = peewee.DecimalField()
    p_mean = peewee.DecimalField()
    p_variance = peewee.DecimalField()
    n_samples = peewee.IntegerField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (price_id, strategy_id)")]


class Tweet(BaseModel):
    time = peewee.DateTimeField()
    text = peewee.TextField()


class Score(BaseModel):
    tweet = peewee.ForeignKeyField(Tweet)
    model = peewee.TextField()
    score = peewee.DecimalField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (tweet_id, model)")]


def get_active_strategies():
    return Strategy \
        .select() \
        .where(Strategy.active) \
        .order_by(Strategy.next_refresh)


def get_pending_strategies():
    now = datetime.datetime.utcnow()
    return get_active_strategies().where((now > Strategy.next_refresh))


def get_tweets_by_model(model: str):
    return Tweet \
        .select(Tweet, Score) \
        .join(Score,
              peewee.JOIN.LEFT_OUTER,
              on=((Score.tweet_id == Tweet.id) & (Score.model == model))) \
        .order_by(Tweet.time)
