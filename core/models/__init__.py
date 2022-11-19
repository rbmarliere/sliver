import importlib
import pathlib

import numpy
import pandas

import core

model_i = "i20221104"
model_p = "p20221019"


def get(model_name):
    model_module = importlib.import_module("core.models." + model_name)
    model = model_module.get_model()
    model.config = model_module.config
    model.tokenizer = model_module.get_tokenizer()
    return model


def load(model_name):
    modelpath = pathlib.Path(core.config["HYPNOX_MODELS_DIR"] + "/" +
                             model_name).resolve()
    assert modelpath.exists()

    model_module = importlib.import_module("core.models." + model_name)
    model = model_module.load_model(modelpath)
    model.config = model_module.config
    model.tokenizer = model_module.get_tokenizer()
    return model


def predict(model, tweets, verbose=0):
    inputs = model.tokenizer(tweets["text"].to_list(),
                             truncation=True,
                             padding="max_length",
                             max_length=model.config["max_length"],
                             return_tensors="tf")

    prob = model.predict(
        {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        },
        batch_size=model.config["batch_size"],
        verbose=verbose)

    if model.config["class"] == "polarity":
        tweets["model_p"] = model.config["name"]

        indexes = prob.argmax(axis=1)
        values = numpy.take_along_axis(prob,
                                       numpy.expand_dims(indexes, axis=1),
                                       axis=1).squeeze(axis=1)
        labels = [-1 if x == 2 else x for x in indexes]

        tweets["polarity"] = labels * values

    elif model.config["class"] == "intensity":
        tweets["model_i"] = model.config["name"]
        tweets["intensity"] = prob.flatten()

    return tweets


def replay(model, update_only=True, verbose=0):
    if model.config["class"] == "intensity":
        filter = core.db.Tweet.model_i.is_null(True)
        fields = ["model_i", "intensity"]
    else:
        filter = core.db.Tweet.model_p.is_null(True)
        fields = ["model_p", "polarity"]

    if not update_only:
        filter = True

    query = core.db.Tweet.select().where(filter).order_by(
        core.db.Tweet.id.asc())

    tweets = pandas.DataFrame(query.dicts())

    if tweets.empty:
        core.watchdog.log.info("no tweets to replay")
        return

    core.watchdog.log.info("replaying " + str(query.count()) +
                           " tweets with model " + model.config["name"])

    tweets.text = tweets.text.apply(core.utils.standardize)
    tweets.text = tweets.text.str.slice(0, model.config["max_length"])

    tweets = predict(model, tweets, verbose=verbose)

    item = 0
    page_size = 8096
    updates = []

    for i, tweet in tweets.iterrows():
        if item == page_size:
            core.db.Tweet.bulk_update(
                updates, fields=fields, batch_size=page_size)
            item = 0
            updates = []

        updates.append(core.db.Tweet(**tweet))
        item += 1

    # final update for last truncated page
    core.db.Tweet.bulk_update(updates, fields=fields)
