import datetime
import decimal
import os

import peewee
import tensorflow
import transformers
from ccxt.base.decimal_to_precision import DECIMAL_PLACES, NO_PADDING, TRUNCATE

import hypnox

# rounding modes:
# TRUNCATE,
# ROUND,
# ROUND_UP,
# ROUND_DOWN,

# precision modes:
# DECIMAL_PLACES,
# SIGNIFICANT_DIGITS,
# TICK_SIZE,

# padding modes:
# NO_PADDING,
# PAD_WITH_ZERO,

connection = peewee.PostgresqlDatabase(
    hypnox.config["HYPNOX_DB_NAME"], **{
        "host": hypnox.config["HYPNOX_DB_HOST"],
        "user": hypnox.config["HYPNOX_DB_USER"],
        "password": hypnox.config["HYPNOX_DB_PASSWORD"]
    })


class BaseModel(peewee.Model):

    class Meta:
        database = connection


class Exchange(BaseModel):
    name = peewee.TextField()
    rate_limit = peewee.IntegerField(default=1200)
    rounding_mode = peewee.IntegerField(default=TRUNCATE)
    precision_mode = peewee.IntegerField(default=DECIMAL_PLACES)
    padding_mode = peewee.IntegerField(default=NO_PADDING)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (name)")]

    def get_market_by_symbol(self, symbol):
        return Market.select().where((Market.exchange == self)
                                     & (Market.symbol == symbol)).get()


class User(BaseModel):
    name = peewee.TextField()
    telegram = peewee.TextField(null=True)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (name)")]

    def get_credential_by_exchange(self, exchange: Exchange):
        return Credential.select().where((Credential.user_id == self.id) & (
            Credential.exchange == exchange)).get()

    # def get_balance_by_asset():


class Credential(BaseModel):
    user = peewee.ForeignKeyField(User)
    exchange = peewee.ForeignKeyField(Exchange)
    api_key = peewee.TextField()
    api_secret = peewee.TextField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, exchange_id)")]


class Asset(BaseModel):
    ticker = peewee.TextField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (ticker)")]


class Market(BaseModel):
    exchange = peewee.ForeignKeyField(Exchange)
    base = peewee.TextField()
    quote = peewee.TextField()
    symbol = peewee.TextField()
    amount_precision = peewee.IntegerField()
    base_precision = peewee.IntegerField()
    price_precision = peewee.IntegerField()
    quote_precision = peewee.IntegerField()
    amount_min = peewee.BigIntegerField()
    cost_min = peewee.BigIntegerField()
    price_min = peewee.BigIntegerField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (exchange_id, symbol)")]

    def bdiv(self, num, den):
        decimal.getcontext().prec = self.base_precision
        div = decimal.Decimal(str(num)) / decimal.Decimal(str(den))

        if abs(num) > abs(den):
            div = int(div)
        else:
            div = self.btransform(div)

        div = hypnox.utils.truncate(self.bformat(div), self.amount_precision)

        return self.btransform(div)

    def qdiv(self, num, den):
        decimal.getcontext().prec = self.quote_precision
        div = decimal.Decimal(str(num)) / decimal.Decimal(str(den))

        if abs(num) > abs(den):
            div = int(div)
        else:
            div = self.btransform(div)

        div = hypnox.utils.truncate(self.qformat(div), self.price_precision)

        return self.qtransform(div)

    def bformat(self, value):
        decimal.getcontext().prec = self.base_precision
        value = decimal.Decimal(str(value)) / 10**self.base_precision
        return hypnox.utils.truncate(value, self.base_precision)

    def qformat(self, value):
        decimal.getcontext().prec = self.quote_precision
        value = decimal.Decimal(str(value)) / 10**self.quote_precision
        return hypnox.utils.truncate(value, self.quote_precision)

    def btransform(self, value):
        decimal.getcontext().prec = self.base_precision
        value = decimal.Decimal(str(value)) * 10**self.base_precision
        return int(value)

    def qtransform(self, value):
        decimal.getcontext().prec = self.base_precision
        value = decimal.Decimal(str(value)) * 10**self.quote_precision
        return int(value)

    def bprint(self, value, format_value=True):
        if format_value:
            value = self.bformat(value)
        prec = str(self.amount_precision)
        return str("{:." + prec + "f} ").format(value) + self.base

    def qprint(self, value, format_value=True):
        if format_value:
            value = self.qformat(value)
        prec = str(self.price_precision)
        return str("{:." + prec + "f} ").format(value) + self.quote


class Strategy(BaseModel):
    market = peewee.ForeignKeyField(Market)
    active = peewee.BooleanField(default=False)
    # description = peewee.TextField()
    timeframe = peewee.TextField(default="1d")
    signal = peewee.TextField(default=hypnox.enum.Signal.NEUTRAL)
    refresh_interval = peewee.IntegerField(default=1)  # 1 minute
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    i_threshold = peewee.DecimalField(default=0)
    p_threshold = peewee.DecimalField(default=0)
    tweet_filter = peewee.TextField(default="")
    num_orders = peewee.IntegerField(default=1)
    bucket_interval = peewee.IntegerField(default=60)  # 1 hour
    spread = peewee.DecimalField(default=1)  # 1%
    min_roi = peewee.DecimalField(default=5)  # 5%
    stop_loss = peewee.DecimalField(default=3)  # -3%

    class Meta:
        constraints = [peewee.SQL("UNIQUE (market_id, active, timeframe)")]

    def get_active_users(self):
        return User.select().join(UserStrategy).join(Strategy).where(
            (Strategy.id == self.id) & (Strategy.market == self.market)
            & (UserStrategy.active))


def get_active_strategies():
    return Strategy.select().where(Strategy.active).order_by(
        Strategy.next_refresh)


def get_pending_strategies():
    now = datetime.datetime.utcnow()
    return get_active_strategies().where((now > Strategy.next_refresh))


class UserStrategy(BaseModel):
    user = peewee.ForeignKeyField(User)
    strategy = peewee.ForeignKeyField(Strategy)
    active = peewee.BooleanField(default=False)

    class Meta:
        constraints = [peewee.SQL("UNIQUE (user_id, strategy_id)")]

    def get_active_position(self):
        return Position.select().join(UserStrategy).join(Strategy).join(
            Market).where((UserStrategy.user_id == self.user_id)
                          & (UserStrategy.strategy_id == self.strategy_id)
                          & ((Position.status == "open")
                             | (Position.status == "opening")
                             | (Position.status == "closing"))).get()


class Position(BaseModel):
    user_strategy = peewee.ForeignKeyField(UserStrategy)
    # time limit on each buy/sell step for DCA
    next_bucket = peewee.DateTimeField(default=datetime.datetime.utcnow())
    # maximum cost|amount for any time period
    bucket_max = peewee.BigIntegerField()
    # effective cost|amount for current period
    bucket = peewee.BigIntegerField(default=0)
    # can be open, opening, closing, closed
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

    def get_open_orders(self):
        query = Order.select().join(Position).where((Position.id == self.id)
                                                    & (Order.status == "open"))
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
    exchange_order_id = peewee.IntegerField(unique=True)
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
        price = market.qtransform(ex_order["price"])
        amount = market.qtransform(ex_order["amount"])
        cost = market.qtransform(ex_order["cost"])
        filled = market.qtransform(ex_order["filled"])

        # check for fees
        if ex_order["fee"] is None:
            fee = 0
        else:
            fee = market.qtransform(ex_order["fee"]["cost"])

        # create model and save
        order = hypnox.db.Order(position=position,
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


class Tweet(BaseModel):
    time = peewee.DateTimeField()
    text = peewee.TextField(null=False)
    model_i = peewee.TextField(default="")
    intensity = peewee.DecimalField(default=0)
    model_p = peewee.TextField(default="")
    polarity = peewee.DecimalField(default=0)


class Inventory(BaseModel):
    user = peewee.ForeignKeyField(User)
    time = peewee.DateTimeField()
    # balances


def replay(args):
    model_config = hypnox.utils.load_yaml("/../lib/models/" + args.model +
                                          ".yaml")
    model_path = hypnox.utils.get_abs_path("/../lib/models/" + args.model)
    assert os.path.exists(model_path)

    bert = transformers.TFAutoModel.from_pretrained(
        model_config["bert"],
        num_labels=model_config["num_labels"],
        from_pt=True)
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        model_config["bert"])

    model = tensorflow.keras.models.load_model(
        model_path, custom_objects={"TFBertModel": bert})

    if model_config["class"] == "polarity":
        model_column = getattr(hypnox.db.Tweet, "model_p")
        score_column = getattr(hypnox.db.Tweet, "polarity")
    elif model_config["class"] == "intensity":
        model_column = getattr(hypnox.db.Tweet, "model_i")
        score_column = getattr(hypnox.db.Tweet, "intensity")

    query = hypnox.db.Tweet.select().where((model_column != args.model)
                                           | (model_column.is_null()))

    tweets = []
    for tweet in query:
        cleaned_text = hypnox.utils.standardize(tweet.text)
        if cleaned_text is not None:
            tweets.append(tweet)
    if not tweets:
        hypnox.watchdog.log.info("no tweets to replay")
        return 1

    inputs = tokenizer([tweet.text for tweet in tweets],
                       truncation=True,
                       padding="max_length",
                       max_length=model_config["max_length"],
                       return_tensors="tf")

    prob = model.predict(
        {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        },
        batch_size=128,
        verbose=1)

    if model_config["class"] == "polarity":
        labels = {0: 0, 2: -1, 1: 1}
        i = 0
        for tweet in tweets:
            tweet.model_p = args.model
            max = prob[i].argmax()
            tweet.polarity = labels[max] * prob[i][max]
            i += 1
    elif model_config["class"] == "intensity":
        i = 0
        for tweet in tweets:
            tweet.model_i = args.model
            tweet.intensity = prob[i][1].item()
            i += 1

    with hypnox.db.connection.atomic():
        hypnox.db.Tweet.bulk_update(tweets,
                                    fields=[model_column, score_column],
                                    batch_size=128)
