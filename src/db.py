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


class BaseModel(peewee.Model):

    class Meta:
        database = connection


# TODO: Order model


class Position(BaseModel):
    market = peewee.TextField(null=False)
    size = peewee.DecimalField(decimal_places=2, auto_round=True)
    amount = peewee.DecimalField(decimal_places=2, auto_round=True)
    entry_time = peewee.DateTimeField()
    entry_price = peewee.DecimalField(decimal_places=2, auto_round=True)
    exit_time = peewee.DateTimeField()
    exit_price = peewee.DecimalField(decimal_places=2, auto_round=True)
    pnl = peewee.DecimalField(decimal_places=2, auto_round=True)

    class Meta:
        table_name = "positions"


class Price(BaseModel):
    # TODO: prices as integers (e.g. float_price * 10)
    time = peewee.DateTimeField(unique=True)
    open = peewee.DecimalField(decimal_places=2, auto_round=True)
    high = peewee.DecimalField(decimal_places=2, auto_round=True)
    low = peewee.DecimalField(decimal_places=2, auto_round=True)
    close = peewee.DecimalField(decimal_places=2, auto_round=True)
    volume = peewee.DecimalField(decimal_places=2, auto_round=True)

    class Meta:
        table_name = "btcusdt_4h"
        primary_key = False


class Tweet(BaseModel):
    time = peewee.DateTimeField()
    text = peewee.TextField(null=False)
    model_i = peewee.TextField(default="")
    intensity = peewee.DecimalField(default=0)
    model_p = peewee.TextField(default="")
    polarity = peewee.DecimalField(default=0)

    class Meta:
        table_name = "tweets"


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

    query = hypnox.db.Tweet.select()
    if args.update_only:
        query = query.where((model_column != model_config.yaml["name"])
                            | (model_column.is_null()))

    tweets = []
    for tweet in query:
        cleaned_text = hypnox.text_utils.standardize(tweet.text)
        if cleaned_text is not None:
            tweets.append(tweet)
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
