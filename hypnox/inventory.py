# TODO check inventory before retrying if an order fails

# --METRICS:
# VaR,
# sharpe,
# TWAP/VWAP,
# cagr,
# sortino,
# cumulative return,
# profit factor,
# max drawdown,
# payoff ratio,
# win days

import hypnox


def get_target_cost(market):
    balance = hypnox.exchange.api.fetch_balance()
    balance = market.qtransform(balance[market.quote]["free"])
    target_cost = market.qdiv(balance, 10)
    return target_cost


def sync_balances(user: hypnox.db.User, market: hypnox.db.Market):
    hypnox.watchdog.log.info("sync_inventory")
    # refresh balances


def report():
    hypnox.watchdog.log.info("report pnl over a period")
