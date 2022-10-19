#!/usr/bin/env python3

import argparse
import pathlib

import pandas

import hypnox.models


def predict(model, tweets):
    inputs = model.tokenizer([tweet.text for tweet in tweets],
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
        labels = {0: 0, 2: -1, 1: 1}
        i = 0
        for tweet in tweets:
            tweet.model_p = model.config["name"]
            max = prob[i].argmax()
            tweet.polarity = labels[max] * prob[i][max]
            i += 1
    elif model.config["class"] == "intensity":
        i = 0
        for tweet in tweets:
            tweet.model_i = model.config["name"]
            tweet.intensity = prob[i][1].item()
            i += 1

    return tweets


def replay_csv(model, filepath):
    print('TODO')
    # data = pandas.read_csv(filepath)
    # # data["clean"] = data["text"].apply(hypnox.utils.standardize)

    # if model.config["class"] == "polarity":
    #     model_column = data["model_p"]
    #     score_column = data["polarity"]
    # elif model.config["class"] == "intensity":
    #     model_column = data["model_i"]
    #     score_column = data["intensity"]

    # # data["polarity"] = model.predict(model)

    # data["intensity"] = data["intensity"].map("{:.4f}".format)
    # data["polarity"] = data["polarity"].map("{:.4f}".format)

    # data = data[["intensity", "polarity", "text"]]
    # data.to_csv("results.csv", index=False)


def replay_db(model):
    if model.config["class"] == "polarity":
        model_column = getattr(hypnox.db.Tweet, "model_p")
        score_column = getattr(hypnox.db.Tweet, "polarity")
    elif model.config["class"] == "intensity":
        model_column = getattr(hypnox.db.Tweet, "model_i")
        score_column = getattr(hypnox.db.Tweet, "intensity")

    query = hypnox.db.Tweet.select().where((
        model_column != model.config["name"])
                                           | (model_column.is_null()))

    tweets = [t for t in query]

    # tweets = []
    # for tweet in query:
    #     cleaned_text = hypnox.utils.standardize(tweet.text)
    #     if cleaned_text is not None:
    #         tweets.append(tweet)
    # if not tweets:
    #     hypnox.watchdog.log.info("no tweets to replay")
    #     return 1

    tweets = predict(model, tweets)

    with hypnox.db.connection.atomic():
        hypnox.db.Tweet.bulk_update(tweets,
                                    fields=[model_column, score_column],
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
