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
        exchange = getattr(ccxt, args.exchange_name)({})
    except AttributeError:
        print("exchange not supported by ccxt")
        sys.exit(1)

    l1 = set([i for i in exchange.timeframes.keys()])
    l2 = set(core.utils.get_timeframes())

    obj = {
        "name": args.exchange_name,
        "rate_limit": exchange.rateLimit,
        "precision_mode": exchange.precisionMode,
        "padding_mode": exchange.paddingMode,
        "timeframes": str(list(l1 & l2))
    }

    exchange = core.db.Exchange(**obj)

    db_exch = core.db.Exchange.get_or_none(name=args.exchange_name)

    if db_exch:
        exchange.id = db_exch.id

    exchange.save()
