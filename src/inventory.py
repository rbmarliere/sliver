# TODO check inventory before retrying if an order fails
# TODO VaR, sharpe, TWAP/VWAP
# TODO strategy table with pair and is_running and inventory?

import src as hypnox


def get_target_cost(market):
    balance = hypnox.exchange.api.fetch_balance()
    balance = market.qtransform(balance[market.quote]["free"])
    target_cost = market.qdiv(balance, 10)
    return target_cost


def sync():
    hypnox.watchdog.log.info("sync_inventory")
    # refresh balances


def report():
    hypnox.watchdog.log.info("report pnl over a period")
