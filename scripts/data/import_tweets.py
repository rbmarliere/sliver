import argparse

import pandas
import tqdm
from langdetect import detect, LangDetectException

import sliver.core
from sliver.strategies.hypnox import HypnoxTweet


def clean(args):
    # id;user;fullname;url;timestamp;replies;likes;retweets;text
    print("reading csv")
    input_df = pandas.read_csv(args.input_file, sep=";", encoding="utf-8")
    input_df = input_df[["timestamp", "text"]]

    print("converting to datetime")
    input_df.timestamp = pandas.to_datetime(input_df.timestamp, utc=True)
    input_df = input_df.rename(columns={"timestamp": "time"})
    input_df.dropna(inplace=True)

    for tweet in tqdm.tqdm(input_df.to_dict("records")):
        try:
            if detect(tweet["text"]) == "en":
                HypnoxTweet.insert(**tweet).execute()
        except (LangDetectException, TypeError):
            continue
        except Exception:
            import code

            code.interact(local=locals())


def main(args):
    # time	text
    print("reading csv")
    input_df = pandas.read_csv(args.input_file, sep="\t", encoding="utf-8")
    input_df = input_df[["time", "text"]]
    input_df.time = pandas.to_datetime(input_df.time, utc=True)

    HypnoxTweet.insert_many(input_df.to_dict("records")).execute()


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-i", "--input-file", help="CSV file to import", required=True)
    argp.add_argument("-c", "--clean", help="Clean the CSV file", action="store_true")
    args = argp.parse_args()

    with sliver.core.connection.atomic():
        if args.clean:
            clean(args)
        else:
            main(args)
