#!/usr/bin/env python3

import argparse

import pandas

import core


def main(args):
    exchange = core.db.Exchange.get(name=args.exchange)

    if (
        args.timeframe not in core.utils.get_timeframes()
        or args.timeframe not in exchange.timeframes
    ):
        raise Exception("Invalid timeframe")

    market = exchange.market_set.where(core.db.Market.symbol == args.symbol).get()

    if args.force:
        core.db.Price.delete().where(core.db.Price.market_id == market.id).where(
            core.db.Price.timeframe == args.timeframe
        ).execute()

    prices_q = core.db.Price.get_by_market(market, args.timeframe)
    prices_df = pandas.DataFrame(prices_q.dicts())

    input_df = pandas.read_csv(args.input_file)
    input_df.time = pandas.to_datetime(input_df.time, unit="s")
    if not prices_df.empty:
        input_df = input_df.loc[input_df.time < prices_df.iloc[0].time].copy()

    if input_df.empty:
        raise Exception("No new data to import")

    input_df = input_df.rename(columns={"Volume": "volume"})
    input_df = input_df[["time", "open", "high", "low", "close", "volume"]]
    input_df["market_id"] = market.id
    input_df["timeframe"] = args.timeframe

    input_df[["open", "high", "low", "close"]] = input_df[
        ["open", "high", "low", "close"]
    ].applymap(lambda x: market.quote.transform(x))

    input_df[["volume"]] = input_df[["volume"]].applymap(
        lambda x: market.base.transform(x)
    )

    ins_count = 0
    rm_count = 0
    ins_count = core.db.Price.insert_many(input_df.to_dict("records")).execute()

    if not prices_df.empty:
        rm_count = (
            core.db.Indicator.delete()
            .where(core.db.Indicator.price_id >= prices_df.iloc[0].id)
            .where(core.db.Indicator.price_id <= prices_df.iloc[-1].id)
            .execute()
        )

    print(f"imported {ins_count.cursor.rowcount} prices")
    print(f"from {input_df.time.min()} to {input_df.time.max()}")
    print(f"removed {rm_count} indicators")


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-i", "--input-file", help="CSV file to import", required=True)
    argp.add_argument(
        "-e", "--exchange", help="Exchange to import data for", required=True
    )
    argp.add_argument(
        "-s", "--symbol", help="Market symbol to import data for", required=True
    )
    argp.add_argument(
        "-t", "--timeframe", help="Timeframe to import data for", required=True
    )
    argp.add_argument("-f", "--force", help="Delete existing data", action="store_true")
    args = argp.parse_args()

    try:
        with core.db.connection.atomic():
            main(args)
    except Exception as e:
        print(e)
