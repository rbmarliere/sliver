import importlib
import pathlib
import sys

import numpy
import pandas

import core


def get(model_name):
    model_module = importlib.import_module("core.models." + model_name)
    model = model_module.get_model()
    model.config = model_module.config
    model.tokenizer = model_module.load_tokenizer()
    return model


def load(model_name):
    try:
        return getattr(sys.modules[__name__], model_name)
    except AttributeError:
        pass

    core.watchdog.info("loading model {m}".format(m=model_name))

    modelpath = pathlib.Path(core.config["HYPNOX_MODELS_DIR"] + "/" +
                             model_name).resolve()
    if not modelpath.exists():
        raise core.errors.ModelDoesNotExist

    model_module = importlib.import_module("core.models." + model_name)
    model = model_module.load_model(modelpath)
    model.config = model_module.config
    model.tokenizer = model_module.load_tokenizer(modelpath=modelpath)

    setattr(sys.modules[__name__], model_name, model)

    return model


def predict(model, tweets, verbose=0):
    inputs = model.tokenizer(tweets,
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
        indexes = prob.argmax(axis=1)
        values = numpy.take_along_axis(prob,
                                       numpy.expand_dims(indexes, axis=1),
                                       axis=1).squeeze(axis=1)
        labels = [-1 if x == 2 else x for x in indexes]

        scores = labels * values

    elif model.config["class"] == "intensity":
        scores = prob.flatten()

    return scores


def replay(model, update_only=True, verbose=0):
    query = core.db.get_tweets_by_model(model.config["name"])

    if update_only:
        query = query.where(core.db.Score.model.is_null())

    tweets = pandas.DataFrame(query.dicts())

    if tweets.empty:
        core.watchdog.info("{m}: no tweets to replay"
                           .format(m=model.config["name"]))
        return

    core.watchdog.info("{m}: replaying {c} tweets"
                       .format(c=query.count(),
                               m=model.config["name"]))

    tweets.text = tweets.text.apply(core.utils.standardize)
    tweets.text = tweets.text.str.slice(0, model.config["max_length"])

    tweets = tweets.rename(columns={"id": "tweet_id"})
    tweets["model"] = model.config["name"]
    tweets["score"] = predict(model, tweets["text"].to_list(), verbose=verbose)

    scores = tweets[["tweet_id", "model", "score"]]
    core.db.Score.insert_many(scores.to_dict("records")).execute()
