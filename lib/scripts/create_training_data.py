#!/usr/bin/env python3

import argparse
import datetime
import logging
import sys

import pandas

sys.path.insert(0, "../..")
logging.basicConfig(format='hypnox: %(levelname)s: %(message)s',
                    level=logging.INFO)

import src as hypnox  # noqa: E402

argp = argparse.ArgumentParser()
argp.add_argument("-i",
                  "--input",
                  help="last training data file",
                  required=True)
argp.add_argument("-n",
                  "--num_lines",
                  help="number of tweets to fetch from top scored",
                  required=True)
args = argp.parse_args()

logging.info("loading input labeled data")
try:
    last_training = pandas.read_csv(args.input,
                                    lineterminator="\n",
                                    delimiter="\t",
                                    encoding="utf-8")
except FileNotFoundError:
    logging.error("input file not found!")
    sys.exit(1)
last_training["clean"] = last_training["tweet"].apply(
    hypnox.utils.standardize)

logging.info("retrieving highest scored tweets set")
query = hypnox.db.Tweet.select().order_by(
    hypnox.db.Tweet.intensity.desc()).limit(args.num_lines)
tweets = pandas.DataFrame(query.dicts())
tweets["clean"] = tweets["text"].apply(hypnox.utils.standardize)

logging.info("fetching 200 most frequent words in the set")
words = tweets.clean.str.split(
    expand=True).stack().value_counts().reset_index()
list_words = words["index"].head(200).values.tolist()

logging.info("filtering tweets that uses at least 3 most frequent words")
match = pandas.concat(
    [tweets.clean.str.contains(word, regex=False) for word in list_words],
    axis=1).sum(1) > 3
filtered = tweets.loc[match].reset_index(drop=True)

logging.info("checking if new tweets aren't labeled already")
dup_filter = pandas.merge(filtered["clean"],
                          last_training["clean"].drop_duplicates(),
                          indicator=True,
                          how="outer").query('_merge=="left_only"')
dup_filtered = filtered.loc[dup_filter.index]["text"]

logging.info("splitting data into 1000 lines chunks")
output_chunks = [
    dup_filtered.values[i:i + 1000]
    for i in range(0, len(dup_filter.values), 1000)
]

logging.info("saving to file")
date = datetime.datetime.now().strftime("%Y%m%d")
i = 1
for output in output_chunks:
    output_df = pandas.DataFrame({
        "intensity": 0,
        "polarity": 0,
        "tweet": output
    })
    output_df.to_csv("training_" + date + "_" + str(i) + ".tsv",
                     sep="\t",
                     line_terminator="\n",
                     encoding="utf-8",
                     index=False)
    i += 1
