#!/usr/bin/env python3

import argparse
import pathlib

import pandas

import hypnox.models


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

        labels = {0: 0, 2: -1, 1: 1}
        i = 0
        for tweet in tweets:
            tweet.model_p = model.config["name"]
            max = prob[i].argmax()
            tweet.polarity = labels[max] * prob[i][max]
            i += 1

    elif model.config["class"] == "intensity":
        tweets["model_i"] = model.config["name"]
        tweets["intensity"] = prob.flatten()

    return tweets


def replay_csv(model, filepath):
    tweets = pandas.read_csv(filepath)

    tweets = predict(model, tweets)

    tweets["intensity"] = tweets["intensity"].map("{:.4f}".format)
    tweets["polarity"] = tweets["polarity"].map("{:.4f}".format)

    tweets.to_csv("results.csv", index=False)


def replay_db(model):
    query = hypnox.db.Tweet.select()

    tweets = pandas.DataFrame(query.dicts())

    tweets = predict(model, tweets)

    updates = []
    for i, tweet in tweets.iterrows():
        updates.append(hypnox.db.Tweet(**tweet))

    with hypnox.db.connection.atomic():
        hypnox.db.Tweet.bulk_update(
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

    model = hypnox.models.load(args.model_name)

    if args.input_file:
        filepath = pathlib.Path().cwd() / args.input_file
        filepath = filepath.resolve()
        assert filepath.is_file()

        replay_csv(model, filepath)

    else:
        replay_db(model)
