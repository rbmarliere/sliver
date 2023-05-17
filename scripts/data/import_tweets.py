import argparse

import pandas
import tqdm
from langdetect import LangDetectException, detect

import sliver.database as db
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
    input_df = input_df.dropna()

    print("inserting into database")
    page_size = 100000
    for i in tqdm.tqdm(range(0, len(input_df), page_size)):
        page = input_df.iloc[i : i + page_size]
        HypnoxTweet.insert_many(page.to_dict("records")).execute()


if __name__ == "__main__":
    db.init()

    argp = argparse.ArgumentParser()
    argp.add_argument("-i", "--input-file", help="CSV file to import", required=True)
    argp.add_argument("-c", "--clean", help="Clean the CSV file", action="store_true")
    args = argp.parse_args()

    with db.connection.atomic():
        if args.clean:
            clean(args)
        else:
            main(args)
