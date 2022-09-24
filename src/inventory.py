# TODO check inventory before retrying if an order fails
# TODO VaR, sharpe, TWAP/VWAP
# TODO strategy table with pair and is_running and inventory?

import src as hypnox


def get_target_cost(market):
    balance = hypnox.exchange.api.fetch_balance()
    quote_bal = balance[market.quote]["free"] / 10
    return market.qtransform(quote_bal)


def sync():
    hypnox.watchdog.log.info("sync_inventory")
    # refresh balances
