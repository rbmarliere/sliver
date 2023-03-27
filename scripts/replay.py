#!/usr/bin/env python3

import argparse
import pathlib
import sys

import pandas

import core
import models
import strategies


def replay_csv(model, filepath):
    tweets = pandas.read_csv(filepath)

    tweets = models.predict(model, tweets)

    tweets["intensity"] = tweets["intensity"].map("{:.4f}".format)
    tweets["polarity"] = tweets["polarity"].map("{:.4f}".format)

    tweets.to_csv(core.cfg("LOGS_DIR") + "/replay_results.csv", index=False)


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-i", "--input-file", help="path to input file containing tweets to replay"
    )
    argp.add_argument(
        "-m",
        "--model-name",
        help="name of model to be used to predict scores",
        required=True,
    )
    argp.add_argument("-u", "--update-only", action="store_true")
    args = argp.parse_args()

    model = models.load_model(args.model_name)

    if args.input_file:
        filepath = pathlib.Path().cwd() / args.input_file
        filepath = filepath.resolve()
        assert filepath.is_file()

        replay_csv(model, filepath)

        sys.exit(0)

    query = strategies.hypnox.HypnoxTweet.get_tweets_by_model(model.config["name"])

    if args.update_only:
        query = query.where(strategies.hypnox.HypnoxScore.model.is_null())

    strategies.hypnox.replay(query, model, verbose=1)
