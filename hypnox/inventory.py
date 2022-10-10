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

import ccxt

import hypnox


def get_inventory(user: hypnox.db.User):
    inventory = {}
    inv_free_val = inv_used_val = inv_total_val = 0

    for asset in hypnox.db.Asset.select():
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


def get_target_cost(user_strat: hypnox.db.UserStrategy):
    user = user_strat.user

    inventory = get_inventory(user)

    net_liquid = inventory["total_value"] - inventory["positions_value"]
    hypnox.watchdog.log.info("net liquid is " + str(net_liquid))

    max_risk = net_liquid * float(user.max_risk)
    hypnox.watchdog.log.info("max risk is " + str(max_risk))

    cash_liquid = inventory["USDT"]["total"] - inventory["positions_reserved"]
    available = cash_liquid * float(user.cash_reserve)
    hypnox.watchdog.log.info("available cash is " + str(available))

    target_cost = min(max_risk, available * float(user.target_factor))
    hypnox.watchdog.log.info("target cost is " + str(target_cost))

    return user_strat.strategy.market.quote.transform(target_cost)


def sync_balances(user: hypnox.db.User):
    value_ticker = "USDT"
    value_asset, new = hypnox.db.Asset.get_or_create(ticker=value_ticker)
    if new:
        hypnox.watchdog.log.info("saved asset " + value_asset.ticker +
                                 " to exchange")

    # backup current api
    curr_cred = hypnox.exchange.credential

    # sync balance for each exchange the user has a key
    for cred in user.credential_set:
        hypnox.watchdog.log.info("fetching user balance in exchange " +
                                 hypnox.exchange.api.id)

        hypnox.exchange.set_api(cred)

        ex_bal = hypnox.exchange.api.fetch_balance()

        ex_val_asset, new = hypnox.db.ExchangeAsset.get_or_create(
            exchange=cred.exchange, asset=value_asset)
        if new:
            hypnox.watchdog.log.info("saved asset " +
                                     ex_val_asset.asset.ticker +
                                     " to exchange")

        # for each exchange asset, update internal user balance
        for ticker in ex_bal["free"]:
            if ex_bal["total"][ticker] == 0:
                continue

            asset, new = hypnox.db.Asset.get_or_create(ticker=ticker.upper())
            if new:
                hypnox.watchdog.log.info("saved new asset " + asset.ticker)

            ex_asset, new = hypnox.db.ExchangeAsset.get_or_create(
                exchange=cred.exchange, asset=asset)
            if new:
                hypnox.watchdog.log.info("saved asset " +
                                         ex_asset.asset.ticker +
                                         " to exchange")

            u_bal, new = hypnox.db.Balance.get_or_create(
                user=user, asset=ex_asset, value_asset=ex_val_asset)
            if new:
                hypnox.watchdog.log.info("saved new balance " + str(u_bal.id))

            u_bal.free = ex_asset.transform(ex_bal["free"][ticker])
            u_bal.used = ex_asset.transform(ex_bal["used"][ticker])
            u_bal.total = ex_asset.transform(ex_bal["total"][ticker])

            try:
                p = hypnox.exchange.api.fetch_ticker(asset.ticker + "/" +
                                                     value_asset.ticker)
                # hypnox.watchdog.log.info("last " + asset.ticker +
                #                          " price is $" + str(p["last"]))

                free_value = p["last"] * ex_bal["free"][ticker]
                used_value = p["last"] * ex_bal["used"][ticker]
                total_value = p["last"] * ex_bal["total"][ticker]

                u_bal.free_value = ex_val_asset.transform(free_value)
                u_bal.used_value = ex_val_asset.transform(used_value)
                u_bal.total_value = ex_val_asset.transform(total_value)

            except ccxt.BadSymbol:
                u_bal.free_value = u_bal.free
                u_bal.used_value = u_bal.used
                u_bal.total_value = u_bal.total

            u_bal.save()

    # restore previous api
    hypnox.exchange.set_api(curr_cred)
