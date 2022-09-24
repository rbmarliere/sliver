#!/usr/bin/env python3

import sys

sys.path.insert(0, "../..")

import src as hypnox  # noqa: E402

table_exists = hypnox.db.Market.table_exists()
if not table_exists:
    hypnox.db.Market.create_table()

hypnox.watchdog.scripts_log.info("fetching all markets from exchange api...")

markets = hypnox.exchange.api.fetch_markets()

for m in markets:
    model = hypnox.db.Market(exchange=hypnox.exchange.api.id,
                             symbol=m["symbol"],
                             base=m["base"],
                             quote=m["quote"],
                             base_precision=m["precision"]["base"],
                             quote_precision=m["precision"]["quote"])

    model.cost_min = int(m["limits"]["cost"]["min"] *
                         10**model.quote_precision)

    model.save(force_insert=table_exists)

    hypnox.watchdog.scripts_log.info("saved market " + model.symbol)
