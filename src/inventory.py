# TODO check inventory before retrying if an order fails
# TODO Any error should notify and/or stop operation
# TODO VaR, sharpe, TWAP/VWAP
# TODO strategy table with pair and is_running and inventory?
import logging

import src as hypnox


def get_inventory(strategy):
    markets = hypnox.exchange.api.fetch_markets()
    balance = hypnox.exchange.api.fetch_balance()  # maybe fetch_free_balance

    base = strategy["SYMBOL"].split("/")[0]
    base_bal = balance[base]["free"]
    quote = strategy["SYMBOL"].split("/")[1]
    quote_bal = balance[quote]["free"]

    logging.info("quote balance is " + str(round(quote_bal, 2)))
    logging.info("base balance is " + str(round(base_bal, 2)))

    for m in markets:
        if m["symbol"] == strategy["SYMBOL"]:
            break

    # {'leverage': {'min': None, 'max': None}, 'amount': {'min': 0.01, 'max': 9000.0}, 'price': {'min': 0.01, 'max': 10000.0}, 'cost': {'min': 10.0, 'max': None}, 'market': {'min': 0.0, 'max':    1000.0}}
    # m["limits"]

    target_cost = balance[quote]["free"] * 0.98
    bucket_max = balance[quote]["free"] / strategy["NUM_ORDERS"]

    # if bucket_max < exch_limit: --

    return target_cost, bucket_max
