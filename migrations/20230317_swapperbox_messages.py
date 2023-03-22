import argparse

import pandas

import core
import strategies


argp = argparse.ArgumentParser()
argp.add_argument(
    "-i", "--input", help="path to messages tsv file", type=str, required=True
)
args = argp.parse_args()

strategies.swapperbox.SwapperBoxMessage.create_table()

with core.db.connection.atomic():
    df = pandas.read_csv(args.input, sep="\t")
    df.date = pandas.to_datetime(df.date, utc=True).dt.tz_localize(None)

    df.rename(columns={"id": "telegram_message_id"}, inplace=True)

    core.strategies.swapperbox.SwapperBoxMessage.insert_many(
        df.to_dict(orient="records")
    ).execute()
