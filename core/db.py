import datetime
import decimal

import peewee
import tensorflow
from ccxt.base.decimal_to_precision import DECIMAL_PLACES, NO_PADDING

import core

tensorflow.get_logger().setLevel('INFO')

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


class User(BaseModel):
    email = peewee.TextField(unique=True)
    password = peewee.TextField()
    access_key = peewee.TextField(unique=True, null=True)
    telegram = peewee.TextField(null=True)
    max_risk = peewee.DecimalField(default=0.1)
    cash_reserve = peewee.DecimalField(default=0.25)
    target_factor = peewee.DecimalField(default=0.1)

    def get_credential_by_exchange_or_none(self, exchange: Exchange):
        return self \
            .credential_set \
            .where(Credential.exchange == exchange) \
            .get_or_none()

    def get_balances_by_asset(self, asset: Asset):
        return Balance \
            .select() \
            .join(ExchangeAsset,
                  on=(Balance.asset_id == ExchangeAsset.asset_id)) \
            .join(Asset) \
            .switch(Balance) \
            .join(User) \
            .where((Balance.user_id == self.id)
                   & (Asset.id == asset.id)) \
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

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, exchange_id)")]


class ExchangeAsset(BaseModel):
    exchange = peewee.ForeignKeyField(Exchange)
    asset = peewee.ForeignKeyField(Asset)
    precision = peewee.IntegerField(default=1)

    def div(self, num, den, trunc_precision=None):
        if trunc_precision is None:
            trunc_precision = self.precision

        decimal.getcontext().prec = self.precision if self.precision > 0 else 1
        div = decimal.Decimal(str(num)) / decimal.Decimal(str(den))

        if abs(num) > abs(den):
            div = int(div)
        else:
            div = self.transform(div)

        div = core.utils.truncate(self.format(div), trunc_precision)

        return self.transform(div)

    def format(self, value):
        decimal.getcontext().prec = self.precision if self.precision > 0 else 1
        value = decimal.Decimal(str(value)) / 10**self.precision
        return core.utils.truncate(value, self.precision)

    def transform(self, value):
        decimal.getcontext().prec = self.precision if self.precision > 0 else 1
        value = decimal.Decimal(str(value)) * 10**self.precision
        return int(value)

    def print(self, value, format_value=True, trunc_precision=None):
        if trunc_precision is None:
            trunc_precision = self.precision

        if format_value:
            value = self.format(value)

        prec = str(trunc_precision)

        return str("{:." + prec + "f} ").format(value) + self.asset.ticker


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
            .order_by(core.db.Price.time)


class UserStrategy(BaseModel):
    user = peewee.ForeignKeyField(User)
    strategy = peewee.ForeignKeyField(Strategy)
    active = peewee.BooleanField(default=False)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, strategy_id)")]

    def get_active_position_or_none(self):
        return Position.select().join(UserStrategy).join(Strategy).join(
            Market).where((UserStrategy.user_id == self.user_id)
                          & (UserStrategy.strategy_id == self.strategy_id)
                          & ((Position.status == "open")
                             | (Position.status == "opening")
                             | (Position.status == "closing"))).get_or_none()


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

    def open(user_strat: UserStrategy, target_cost: int):
        strategy = user_strat.strategy
        now = datetime.datetime.utcnow()
        next_bucket = now + datetime.timedelta(
            minutes=strategy.bucket_interval)

        bucket_max = strategy.market.quote.div(
            target_cost,
            strategy.num_orders,
            trunc_precision=strategy.market.price_precision)

        position = core.db.Position(user_strategy=user_strat,
                                    next_bucket=next_bucket,
                                    bucket_max=bucket_max,
                                    status="opening",
                                    target_cost=target_cost)
        position.save()

        core.watchdog.log.info("opened position " + str(position.id))

        return position

    def get_orders(self):
        return Order \
            .select(Order, Strategy.id.alias("strategy_id")) \
            .join(Position) \
            .join(UserStrategy) \
            .join(Strategy) \
            .where((Order.status != "canceled") | (Order.filled > 0)) \
            .order_by(Order.time.desc())

    def get_open_orders(self):
        query = self.get_orders().where(Order.status == "open")
        return [order for order in query]

    def is_open(self):
        return self.status != "closing" and self.status != "closed"

    def get_remaining_to_fill(self):
        return self.bucket_max - self.bucket

    def get_remaining_to_exit(self):
        return self.entry_amount - self.exit_amount

    def get_remaining_to_open(self):
        return min(self.target_cost - self.entry_cost,
                   self.bucket_max - self.bucket)


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

    def create_from_ex_order(ex_order, position):
        market = position.user_strategy.strategy.market

        # transform values to db entry standard
        price = market.quote.transform(ex_order["price"])
        amount = market.quote.transform(ex_order["amount"])
        cost = market.quote.transform(ex_order["cost"])
        filled = market.quote.transform(ex_order["filled"])

        # check for fees
        if ex_order["fee"] is None:
            fee = 0
        else:
            fee = market.quote.transform(ex_order["fee"]["cost"])

        # create model and save
        order = core.db.Order(position=position,
                              exchange_order_id=ex_order["id"],
                              time=ex_order["datetime"],
                              status=ex_order["status"],
                              type=ex_order["type"],
                              side=ex_order["side"],
                              price=price,
                              amount=amount,
                              cost=cost,
                              filled=filled,
                              fee=fee)
        order.save()


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
    model_i = peewee.TextField(null=True)
    intensity = peewee.DecimalField(null=True)
    model_p = peewee.TextField(null=True)
    polarity = peewee.DecimalField(null=True)


def get_active_strategies():
    return Strategy \
        .select() \
        .where(Strategy.active) \
        .order_by(Strategy.next_refresh)


def get_pending_strategies():
    now = datetime.datetime.utcnow()
    return get_active_strategies().where((now > Strategy.next_refresh))
