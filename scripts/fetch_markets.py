#!/usr/bin/env python3

import argparse
import sys

import core


def save_market(ex_market, exchange: core.db.Exchange):
    with core.db.connection.atomic():
        if not ex_market["spot"]:
            return

        try:
            amount_prec = ex_market["precision"]["amount"]
            if amount_prec is None:
                print("using default amount_prec = 8")
                amount_prec = 8
        except KeyError:
            print("using default amount_prec = 8")
            amount_prec = 8

        try:
            price_prec = ex_market["precision"]["price"]
            if price_prec is None:
                print("using default amount_prec = 2")
                price_prec = 2
        except KeyError:
            print("using default amount_prec = 2")
            price_prec = 2

        try:
            base_prec = ex_market["precision"]["base"]
            if base_prec is None:
                print("using base_prec = amount_prec")
                base_prec = amount_prec
        except KeyError:
            print("using base_prec = amount_prec")
            base_prec = amount_prec

        try:
            quote_prec = ex_market["precision"]["quote"]
            if quote_prec is None:
                print("using quote_prec = price_prec")
                quote_prec = price_prec
        except KeyError:
            print("using quote_prec = price_prec")
            quote_prec = price_prec

        base, new = (core.db.Asset
                     .get_or_create(ticker=ex_market["base"]))
        quote, new = (core.db.Asset
                      .get_or_create(ticker=ex_market["quote"]))

        ex_b, new = core.db.ExchangeAsset.get_or_create(
            asset=base,
            exchange=exchange)
        ex_b.precision = base_prec
        ex_b.save()

        ex_q, new = core.db.ExchangeAsset.get_or_create(
            asset=quote,
            exchange=exchange)
        ex_q.precision = quote_prec
        ex_q.save()

        m, new = core.db.Market.get_or_create(base=ex_b, quote=ex_q)

        m.amount_precision = amount_prec
        m.price_precision = price_prec

        try:
            amount_min = ex_market["limits"]["amount"]["min"]
            if amount_min is None:
                print("using default amount_min = 0.0001")
                amount_min = 0.0001
        except KeyError:
            print("using default amount_min = 0.0001")
            amount_min = 0.0001

        try:
            cost_min = ex_market["limits"]["cost"]["min"]
            if cost_min is None:
                print("using default cost_min = 10")
                cost_min = 10
        except KeyError:
            print("using default cost_min = 10")
            cost_min = 10

        try:
            price_min = ex_market["limits"]["price"]["min"]
            if price_min is None:
                print("using default price_min = 1")
                price_min = 1
        except KeyError:
            print("using default price_min = 1")
            price_min = 1

        m.amount_min = m.base.transform(amount_min)
        m.cost_min = m.quote.transform(cost_min)
        m.price_min = m.quote.transform(price_min)

        m.save()


def fetch_markets(exchange: core.db.Exchange):
    print("fetching all markets from exchange api...")
    ex_markets = core.exchange.api.fetch_markets()

    count = 0
    for ex_market in ex_markets:
        core.exchange.save_market(ex_market, exchange)
        count += 1

    print("saved {c} new markets".format(c=count))


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-e",
                      "--exchange-name",
                      help="exchange name to fetch from",
                      required=True)
    argp.add_argument("-s",
                      "--symbol",
                      help="specify a single market to fetch")
    args = argp.parse_args()

    try:
        exchange = core.db.Exchange.get(name=args.exchange_name)
    except core.db.Exchange.DoesNotExist:
        print("exchange not found in database")
        sys.exit(1)

    core.exchange.set_api(exchange=exchange)

    if args.symbol:
        core.exchange.api.load_markets()
        save_market(core.exchange.api.market(args.symbol), exchange)
    else:
        fetch_markets(exchange)
