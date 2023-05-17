import argparse

import pandas

import sliver.database as db
from sliver.strategies.hypnoxv2 import Hypnoxv2Gram


def main(args):
    print("reading csv")
    df = pandas.read_csv(args.input_file, sep="\t", encoding="utf-8")
    df = df[["label", "gram"]]
    df = df.dropna()
    df["rank"] = args.rank

    if args.reset:
        Hypnoxv2Gram.delete().execute()

    print("inserting into database")
    Hypnoxv2Gram.insert_many(df.to_dict("records")).execute()


if __name__ == "__main__":
    db.init()

    argp = argparse.ArgumentParser()
    argp.add_argument("-i", "--input-file", help="CSV file to import", required=True)
    argp.add_argument("-r", "--rank", help="Rank of the n-grams", required=True)
    argp.add_argument(
        "--reset", help="Delete all before inserting", action="store_true"
    )
    args = argp.parse_args()

    with db.connection.atomic():
        Hypnoxv2Gram.create_table()
        main(args)
