#!/usr/bin/env python3

import argparse

import core


def fetch_markets(exchange: core.db.Exchange):
    core.watchdog.log.info("fetching all markets from exchange api...")

    ex_markets = core.exchange.api.fetch_markets()

    for ex_market in ex_markets:
        base, new = core.db.Asset.get_or_create(ticker=ex_market["base"])
        if new:
            core.watchdog.log.info("saved new asset " + base.ticker)

        quote, new = core.db.Asset.get_or_create(ticker=ex_market["quote"])
        if new:
            core.watchdog.log.info("saved new asset " + quote.ticker)

        ex_b, new = core.db.ExchangeAsset.get_or_create(asset=base,
                                                        exchange=exchange)
        if new:
            core.watchdog.log.info("saved asset " + ex_b.asset.ticker +
                                   " to exchange")

        ex_q, new = core.db.ExchangeAsset.get_or_create(asset=quote,
                                                        exchange=exchange)
        if new:
            core.watchdog.log.info("saved asset " + ex_q.asset.ticker +
                                   " to exchange")

        ex_b.precision = ex_market["precision"]["base"]
        ex_b.save()

        ex_q.precision = ex_market["precision"]["quote"]
        ex_q.save()

        m, new = core.db.Market.get_or_create(base=ex_b, quote=ex_q)
        if new:
            core.watchdog.log.info("saved new market " + m.get_symbol())

        m.amount_precision = ex_market["precision"]["amount"]
        m.price_precision = ex_market["precision"]["price"]
        m.amount_min = m.base.transform(ex_market["limits"]["amount"]["min"])
        m.cost_min = m.quote.transform(ex_market["limits"]["cost"]["min"])
        m.price_min = m.quote.transform(ex_market["limits"]["price"]["min"])

        m.save()


if __name__ == "__main__":
    core.watchdog.set_logger("scripts")

    argp = argparse.ArgumentParser()
    argp.add_argument("-e",
                      "--exchange_name",
                      help="exchange name to fetch from",
                      required=True)
    args = argp.parse_args()
    exchange = core.db.Exchange.get(name=args.exchange_name)
    cred = exchange.credential_set.get()
    core.exchange.set_api(cred=cred)
    fetch_markets(exchange)
