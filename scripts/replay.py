#!/usr/bin/env python3

import argparse
import pathlib

import numpy
import pandas

import core.models


def predict(model, tweets):
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
        verbose=1)

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


def replay_csv(model, filepath):
    tweets = pandas.read_csv(filepath)

    tweets = predict(model, tweets)

    tweets["intensity"] = tweets["intensity"].map("{:.4f}".format)
    tweets["polarity"] = tweets["polarity"].map("{:.4f}".format)

    tweets.to_csv(core.config["HYPNOX_LOGS_DIR"] + "/replay_results.csv",
                  index=False)


def replay_db(model):
    query = core.db.Tweet.select()

    tweets = pandas.DataFrame(query.dicts())

    tweets = predict(model, tweets)

    updates = []
    for i, tweet in tweets.iterrows():
        updates.append(core.db.Tweet(**tweet))

    with core.db.connection.atomic():
        core.db.Tweet.bulk_update(
            updates,
            fields=["model_i", "intensity", "model_p", "polarity"],
            batch_size=model.config["batch_size"])


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-i",
                      "--input-file",
                      help="path to input file containing tweets to replay")
    argp.add_argument("-m",
                      "--model-name",
                      help="name of model to be used to predict scores",
                      required=True)
    args = argp.parse_args()

    model = core.models.load(args.model_name)

    if args.input_file:
        filepath = pathlib.Path().cwd() / args.input_file
        filepath = filepath.resolve()
        assert filepath.is_file()

        replay_csv(model, filepath)

    else:
        replay_db(model)
