#!/usr/bin/env python3

import sys

sys.path.insert(0, "../..")

import src as hypnox  # noqa: E402

table_exists = hypnox.db.Market.table_exists()
if not table_exists:
    hypnox.db.Market.create_table()

hypnox.watchdog.scripts_log.info("fetching all markets from exchange api...")

precision_mode = hypnox.exchange.api.precisionMode

ex_markets = hypnox.exchange.api.fetch_markets()

for ex_market in ex_markets:
    market = hypnox.db.Market(
        exchange=hypnox.exchange.api.id,
        symbol=ex_market["symbol"],
        base=ex_market["base"],
        quote=ex_market["quote"],
        precision_mode=precision_mode,
        amount_precision=ex_market["precision"]["amount"],
        base_precision=ex_market["precision"]["base"],
        price_precision=ex_market["precision"]["price"],
        quote_precision=ex_market["precision"]["quote"])

    amount_min = ex_market["limits"]["amount"]["min"]
    cost_min = ex_market["limits"]["cost"]["min"]
    price_min = ex_market["limits"]["price"]["min"]

    market.amount_min = market.btransform(amount_min)
    market.cost_min = market.qtransform(cost_min)
    market.price_min = market.qtransform(price_min)

    market.save(force_insert=table_exists)

    hypnox.watchdog.scripts_log.info("saved market " + market.symbol)
