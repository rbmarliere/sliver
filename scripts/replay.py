#!/usr/bin/env python3

import argparse
import pathlib

import pandas

import core


def replay_csv(model, filepath):
    tweets = pandas.read_csv(filepath)

    tweets = core.models.predict(model, tweets)

    tweets["intensity"] = tweets["intensity"].map("{:.4f}".format)
    tweets["polarity"] = tweets["polarity"].map("{:.4f}".format)

    tweets.to_csv(core.config["HYPNOX_LOGS_DIR"] + "/replay_results.csv",
                  index=False)


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-i",
                      "--input-file",
                      help="path to input file containing tweets to replay")
    argp.add_argument("-m",
                      "--model-name",
                      help="name of model to be used to predict scores",
                      required=True)
    argp.add_argument("-u",
                      "--update-only",
                      action="store_true")
    args = argp.parse_args()

    model = core.models.load(args.model_name)

    if args.input_file:
        filepath = pathlib.Path().cwd() / args.input_file
        filepath = filepath.resolve()
        assert filepath.is_file()

        replay_csv(model, filepath)

    else:
        core.models.replay(model, update_only=args.update_only, verbose=1)
