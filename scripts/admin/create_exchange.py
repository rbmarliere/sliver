import argparse
import sys

import ccxt

import sliver.database as db
from sliver.exchange import Exchange
from sliver.exchanges.types import ExchangeTypes
from sliver.utils import get_timeframes

if __name__ == "__main__":
    db.init()

    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-e", "--exchange-name", help="exchange name to fetch from", required=True
    )
    argp.add_argument("-t", "--type", help="exchange type", type=int, default=0)
    argp.add_argument("--api-endpoint", help="exchange api endpoint")
    argp.add_argument("--api-sandbox-endpoint", help="exchange api sandbox endpoint")
    args = argp.parse_args()

    timeframes = ["15m", "30m", "4h", "1h", "1w", "1d"]

    obj = {
        "name": args.exchange_name,
        "type": args.type,
        "rate_limit": 1000,
        "precision_mode": 0,
        "padding_mode": 0,
        "timeframes": timeframes,
        "api_endpoint": args.api_endpoint,
        "api_sandbox_endpoint": args.api_sandbox_endpoint,
    }

    if args.type == ExchangeTypes.CCXT:
        try:
            exchange = getattr(ccxt, args.exchange_name)({})
        except AttributeError:
            print("exchange not supported by ccxt")
            sys.exit(1)

        l1 = set([i for i in exchange.timeframes.keys()])
        l2 = set(get_timeframes())
        timeframes = str(list(l1 & l2))
        if timeframes:
            obj["timeframes"] = timeframes

        obj["precision_mode"] = exchange.precisionMode
        obj["padding_mode"] = exchange.paddingMode

    exchange = Exchange(**obj)

    db_exch = Exchange.get_or_none(name=args.exchange_name)

    if db_exch:
        exchange.id = db_exch.id

    exchange.save()
