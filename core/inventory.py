# VaR,
# sharpe,
# TWAP/VWAP,
# cagr,
# sterling, calmar, sortino, mar
# cumulative return,
# profit factor,
# max drawdown,
# payoff ratio,
# win days

import core


def get_inventory(user: core.db.User):
    inventory = {}
    inv_free_val = inv_used_val = inv_total_val = 0

    for asset in core.db.Asset.select():
        for bal in user.get_balances_by_asset(asset):
            if bal.total_value == 0:
                continue

            asset = bal.asset.asset

            if asset.ticker not in inventory:
                inventory[asset.ticker] = {
                    "free": 0,
                    "used": 0,
                    "total": 0,
                    "free_value": 0,
                    "used_value": 0,
                    "total_value": 0
                }

            free = bal.asset.format(bal.free)
            used = bal.asset.format(bal.used)
            total = bal.asset.format(bal.total)
            inventory[asset.ticker]["free"] += free
            inventory[asset.ticker]["used"] += used
            inventory[asset.ticker]["total"] += total

            free_val = bal.value_asset.format(bal.free_value)
            used_val = bal.value_asset.format(bal.used_value)
            total_val = bal.value_asset.format(bal.total_value)
            inventory[asset.ticker]["free_value"] += free_val
            inventory[asset.ticker]["used_value"] += used_val
            inventory[asset.ticker]["total_value"] += total_val

            inv_free_val += free_val
            inv_used_val += used_val
            inv_total_val += total_val

    inventory["free_value"] = inv_free_val
    inventory["used_value"] = inv_used_val
    inventory["total_value"] = inv_total_val

    inventory["positions_reserved"] = 0
    inventory["positions_value"] = 0
    for pos in user.get_open_positions():
        pos_asset = pos.user_strategy.strategy.market.quote
        inventory["positions_reserved"] += pos_asset.format(pos.target_cost)
        inventory["positions_value"] += pos_asset.format(pos.exit_cost -
                                                         pos.entry_cost)

    return inventory


def get_target_cost(user_strat: core.db.UserStrategy):
    user = user_strat.user
    exchange = user_strat.strategy.market.base.exchange
    print = user_strat.strategy.market.quote.print
    transform = user_strat.strategy.market.quote.transform

    inventory = get_inventory(user)

    net_liquid = transform(inventory["total_value"]
                           - inventory["positions_value"])
    core.watchdog.info("net liquid is {v}"
                       .format(v=print(net_liquid)))

    max_risk = net_liquid * user.max_risk
    core.watchdog.info("max risk is {v}"
                       .format(v=print(max_risk)))

    q = (user
         .get_balances_by_asset(user_strat.strategy.market.quote.asset)
         .where(core.db.ExchangeAsset.exchange == exchange))
    available_in_exch = [b for b in q]
    if not available_in_exch:
        available_in_exch = 0
    else:
        if available_in_exch[0].free > 0:  # some exchanges dont use this
            cash_in_exch = available_in_exch[0].free
        else:
            cash_in_exch = available_in_exch[0].total
    core.watchdog.info("available {a} in exchange is {v}"
                       .format(a=user_strat.strategy.market.quote.asset.ticker,
                               v=print(cash_in_exch)))

    cash_liquid = transform(inventory["USDT"]["total"]
                            - inventory["positions_reserved"])
    available = min(cash_in_exch, cash_liquid) * (1 - user.cash_reserve)
    core.watchdog.info("available cash is {v}"
                       .format(v=print(available)))

    target_cost = min(max_risk, available * user.target_factor)
    core.watchdog.info("target cost is {v}"
                       .format(v=print(target_cost)))

    return target_cost


# def refresh_targets(user):
#   this method will update target costs based on new risk parameters
#   it will effectively deleverage by reducing open positions to fit new params


def sync_balances(user: core.db.User):
    # backup current api
    curr_cred = None
    if hasattr(core.exchange, "credential"):
        curr_cred = core.exchange.credential

    # sync balance for each exchange the user has a key
    for cred in user.credential_set.where(core.db.Credential.active):
        core.watchdog.info("fetching user balance in exchange {e}"
                           .format(e=cred.exchange.name))

        core.exchange.set_api(cred=cred)

        core.exchange.sync_balance(cred)

    # restore previous api
    if curr_cred:
        core.exchange.set_api(cred=curr_cred)
