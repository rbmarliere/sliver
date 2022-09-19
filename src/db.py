import datetime

import numpy
import peewee
import tensorflow
import transformers

import src as hypnox

connection = peewee.PostgresqlDatabase(
    hypnox.config.config["DB_DATABASE"], **{
        "host": hypnox.config.config["DB_HOST"],
        "user": hypnox.config.config["DB_USER"],
        "password": hypnox.config.config["DB_PASSWORD"]
    })


class CurrencyField(peewee.DecimalField):

    def __init__(self):
        peewee.DecimalField.__init__(self)
        self.auto_round = False
        self.decimal_places = 8
        self.default = 0
        self.max_digits = 16


class BaseModel(peewee.Model):

    class Meta:
        database = connection


class Position(BaseModel):
    # which exchange its at
    exchange = peewee.TextField()
    # e.g. BTCUSDT where BTC is base USDT is quote
    symbol = peewee.TextField()
    # time limit on each buy/sell step for DCA
    next_bucket = peewee.DateTimeField(default=datetime.datetime.utcnow())
    # maximum cost|amount for any time period
    bucket_max = CurrencyField()
    # effective cost|amount for current period
    bucket = CurrencyField()
    # can be open, opening, closing, closed
    status = peewee.TextField()
    # desired position size in quote
    target_cost = CurrencyField()
    # total effective cost paid in quote
    entry_cost = CurrencyField()
    # total amount in base
    entry_amount = CurrencyField()
    # average prices in quote
    entry_price = CurrencyField()
    exit_price = CurrencyField()
    exit_amount = CurrencyField()
    exit_cost = CurrencyField()
    # total fees in quote
    fee = CurrencyField()
    # position profit or loss
    pnl = CurrencyField()

    def get_remaining_to_open(self):
        return min(self.target_cost - self.entry_cost,
                   self.bucket_max - self.bucket)

    def get_remaining_to_close(self):
        return min(self.entry_amount - self.exit_amount,
                   self.bucket_max - self.bucket)


class Order(BaseModel):
    # which exchange its at
    exchange = peewee.TextField()
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
    price = CurrencyField()
    # total order size in base
    amount = CurrencyField()
    # effective order cost in quote
    cost = CurrencyField()
    # effective amount filled in base
    filled = CurrencyField()
    # effective fee paid
    fee = CurrencyField()

    def create_from_ex_order(ex_order, position):
        order = hypnox.db.Order(position=position,
                                exchange_order_id=ex_order["id"],
                                time=ex_order["datetime"],
                                status=ex_order["status"],
                                type=ex_order["type"],
                                side=ex_order["side"],
                                price=ex_order["price"],
                                amount=ex_order["amount"],
                                cost=ex_order["cost"],
                                filled=ex_order["filled"],
                                fee=ex_order["fee"])
        order.save()


class Price(BaseModel):
    exchange = peewee.TextField()
    symbol = peewee.TextField()
    timeframe = peewee.TextField()
    time = peewee.DateTimeField()
    open = CurrencyField()
    high = CurrencyField()
    low = CurrencyField()
    close = CurrencyField()
    volume = CurrencyField()


class Tweet(BaseModel):
    time = peewee.DateTimeField()
    text = peewee.TextField(null=False)
    model_i = peewee.TextField(default="")
    intensity = peewee.DecimalField(default=0)
    model_p = peewee.TextField(default="")
    polarity = peewee.DecimalField(default=0)


def get_open_orders(symbol):
    return Order.select().join(Position).where((Position.symbol == symbol)
                                               & (Order.status == "open"))


def get_active_position(symbol):
    return Position.select().where((Position.symbol == symbol)
                                   & ((Position.status == "open")
                                      | (Position.status == "opening")
                                      | (Position.status == "closing")))


def replay(args):
    model_config = hypnox.config.ModelConfig(args.model)
    model_config.check_model()

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
        model_column != model_config.yaml["name"])
                                           | (model_column.is_null()))

    tweets = []
    for tweet in query:
        cleaned_text = hypnox.text_utils.standardize(tweet.text)
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
        verbose=1)

    if model_config.yaml["class"] == "polarity":
        labels = {0: 0, 2: -1, 1: 1}
        i = 0
        for tweet in tweets:
            tweet.model_p = model_config.yaml["name"]
            max = numpy.argmax(prob[i]).item()
            tweet.polarity = labels[max] * prob[i][max]
            i += 1
    elif model_config.yaml["class"] == "intensity":
        i = 0
        for tweet in tweets:
            tweet.model_i = model_config.yaml["name"]
            tweet.intensity = prob[i][1].item()
            i += 1

    with hypnox.db.connection.atomic():
        hypnox.db.Tweet.bulk_update(tweets,
                                    fields=[model_column, score_column],
                                    batch_size=1024)
