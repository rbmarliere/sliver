#!/usr/bin/env python3
import argparse

import hypnox


def fetch_markets(exchange: hypnox.db.Exchange):
    hypnox.watchdog.script_log.info(
        "fetching all markets from exchange api...")

    ex_markets = hypnox.exchange.api.fetch_markets()

    for ex_market in ex_markets:
        base, new = hypnox.db.Asset.get_or_create(ticker=ex_market["base"])
        if new:
            hypnox.watchdog.log.info("saved new asset " + base.ticker)

        quote, new = hypnox.db.Asset.get_or_create(ticker=ex_market["quote"])
        if new:
            hypnox.watchdog.log.info("saved new asset " + quote.ticker)

        ex_b, new = hypnox.db.ExchangeAsset.get_or_create(asset=base,
                                                          exchange=exchange)
        if new:
            hypnox.watchdog.log.info("saved asset " + ex_b.asset.ticker +
                                     " to exchange")

        ex_q, new = hypnox.db.ExchangeAsset.get_or_create(asset=quote,
                                                          exchange=exchange)
        if new:
            hypnox.watchdog.log.info("saved asset " + ex_q.asset.ticker +
                                     " to exchange")

        ex_b.precision = ex_market["precision"]["base"]
        ex_b.save()

        ex_q.precision = ex_market["precision"]["quote"]
        ex_q.save()

        m, new = hypnox.db.Market.get_or_create(base=ex_b, quote=ex_q)
        if new:
            hypnox.watchdog.script_log.info("saved new market " +
                                            m.get_symbol())

        m.amount_precision = ex_market["precision"]["amount"]
        m.price_precision = ex_market["precision"]["price"]
        m.amount_min = m.base.transform(ex_market["limits"]["amount"]["min"])
        m.cost_min = m.quote.transform(ex_market["limits"]["cost"]["min"])
        m.price_min = m.quote.transform(ex_market["limits"]["price"]["min"])

        m.save()


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-e",
                      "--exchange_name",
                      help="exchange name to fetch from",
                      required=True)
    args = argp.parse_args()
    exchange = hypnox.db.Exchange.get(name=args.exchange_name)
    cred = exchange.credential_set.get()
    hypnox.exchange.set_api(cred)
    fetch_markets(exchange)
