import datetime
import decimal
import os

import peewee
import tensorflow
import transformers

import src as hypnox

connection = peewee.PostgresqlDatabase(
    hypnox.config["DB_DATABASE"], **{
        "host": hypnox.config["DB_HOST"],
        "user": hypnox.config["DB_USER"],
        "password": hypnox.config["DB_PASSWORD"]
    })


class BaseModel(peewee.Model):

    class Meta:
        database = connection


class Market(BaseModel):
    exchange = peewee.TextField()
    symbol = peewee.TextField()
    base = peewee.TextField()
    quote = peewee.TextField()
    precision_mode = peewee.TextField()  # TODO ccxt.base.decimal_to_precision
    amount_precision = peewee.IntegerField()
    base_precision = peewee.IntegerField()
    price_precision = peewee.IntegerField()
    quote_precision = peewee.IntegerField()
    amount_min = peewee.BigIntegerField()
    cost_min = peewee.BigIntegerField()
    price_min = peewee.BigIntegerField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (exchange, symbol)")]

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

    def get_open_orders(self):
        query = Order.select().join(Position).join(Market).where(
            (Market.exchange == self.exchange) & (Market.symbol == self.symbol)
            & (Order.status == "open"))
        return [order for order in query]

    def get_active_position(self):
        return Position.select().join(Market).where(
            (Market.exchange == self.exchange) & (Market.symbol == self.symbol)
            & ((Position.status == "open")
               | (Position.status == "opening")
               | (Position.status == "closing"))).get_or_none()


class Position(BaseModel):
    market = peewee.ForeignKeyField(Market)
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
        # transform values to db entry standard
        price = position.market.qtransform(ex_order["price"])
        amount = position.market.qtransform(ex_order["amount"])
        cost = position.market.qtransform(ex_order["cost"])
        filled = position.market.qtransform(ex_order["filled"])

        # check for fees
        if ex_order["fee"] is None:
            fee = 0
        else:
            fee = position.market.qtransform(ex_order["fee"]["cost"])

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


# class Inventory(BaseModel):
#     time = peewee.DateTimeField()
#     # balances

# class Strategy(BaseModel):


def get_market(exchange, symbol):
    return Market.select().where((Market.exchange == exchange)
                                 & (Market.symbol == symbol)).get_or_none()


def replay(args):
    model_config = hypnox.utils.load_yaml("/../lib/models/" + args.model +
                                          ".yaml")
    model_path = hypnox.utils.get_abs_path("/../lib/models/" + args.model)
    assert os.path.exists(model_path)

    bert = transformers.TFAutoModel.from_pretrained(
        model_config.yaml["bert"],
        num_labels=model_config.yaml["num_labels"],
        from_pt=True)
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        model_config.yaml["bert"])

    model = tensorflow.keras.models.load_model(
        model_config.model_path, custom_objects={"TFBertModel": bert})

    if model_config.yaml["class"] == "polarity":
        model_column = getattr(hypnox.db.Tweet, "model_p")
        score_column = getattr(hypnox.db.Tweet, "polarity")
    elif model_config.yaml["class"] == "intensity":
        model_column = getattr(hypnox.db.Tweet, "model_i")
        score_column = getattr(hypnox.db.Tweet, "intensity")

    query = hypnox.db.Tweet.select().where((
        model_column != args.model)
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
                       max_length=model_config.yaml["max_length"],
                       return_tensors="tf")

    prob = model.predict(
        {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        },
        batch_size=128,
        verbose=1)

    if model_config.yaml["class"] == "polarity":
        labels = {0: 0, 2: -1, 1: 1}
        i = 0
        for tweet in tweets:
            tweet.model_p = args.model
            max = prob[i].argmax()
            tweet.polarity = labels[max] * prob[i][max]
            i += 1
    elif model_config.yaml["class"] == "intensity":
        i = 0
        for tweet in tweets:
            tweet.model_i = args.model
            tweet.intensity = prob[i][1].item()
            i += 1

    with hypnox.db.connection.atomic():
        hypnox.db.Tweet.bulk_update(tweets,
                                    fields=[model_column, score_column],
                                    batch_size=128)
