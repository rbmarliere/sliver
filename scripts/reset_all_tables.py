#!/usr/bin/env python3

import argparse

import core
import strategies


def reset_tables(drop_tables=False):
    tables = [
        core.db.Indicator,
        core.db.Price,
        core.db.Order,
        core.db.Position,
        core.db.UserStrategy,
        core.db.Strategy,
        core.db.Market,
        core.db.Credential,
        core.db.Balance,
        core.db.ExchangeAsset,
        core.db.Exchange,
        core.db.User,
        core.db.Asset,

        strategies.manual.ManualStrategy,

        strategies.random.RandomStrategy,

        strategies.hypnox.HypnoxIndicator,
        strategies.hypnox.HypnoxStrategy,
        strategies.hypnox.HypnoxScore,
        strategies.hypnox.HypnoxTweet,
    ]

    if drop_tables:
        core.db.connection.drop_tables(tables)

    core.db.connection.create_tables(tables)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop_tables", action="store_true")
    args = parser.parse_args()

    reset_tables(args.drop_tables)
