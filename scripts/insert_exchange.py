#!/usr/bin/env python3

import argparse
import sys

import ccxt

import core

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-e",
                      "--exchange-name",
                      help="exchange name to fetch from",
                      required=True)
    args = argp.parse_args()

    try:
        exchange = getattr(ccxt, args.exchange_name)
    except AttributeError:
        print("exchange not supported by ccxt")
        sys.exit(1)

    if core.db.Exchange.get_or_none(name=args.exchange_name):
        print("exchange already in database")
        sys.exit(1)

    core.db.Exchange.create(
        name=args.exchange_name,
        rate_limit=exchange.rateLimit,
        precision_mode=exchange.precisionMode,
        padding_mode=exchange.paddingMode)
