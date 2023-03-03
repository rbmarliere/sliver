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

import core
from core.watchdog import info as i


def get_balance_by_exchange_asset(user: core.db.User,
                                  asset: core.db.ExchangeAsset):
    cred = user.get_active_credential(asset.exchange).get()
    sync_balance(cred)
    return core.db.Balance.get(user_id=user.id, asset_id=asset.id)


def get_balance_by_asset(user: core.db.User, asset: core.db.Asset):
    balance = {
        "ticker": asset.ticker,
        "free": 0,
        "used": 0,
        "total": 0,
        "free_value": 0,
        "used_value": 0,
        "total_value": 0
    }

    for bal in user.get_balances_by_asset(asset):
        if bal.total_value == 0:
            continue

        asset = bal.asset.asset

        free = bal.asset.format(bal.free)
        used = bal.asset.format(bal.used)
        total = bal.asset.format(bal.total)
        balance["free"] += free
        balance["used"] += used
        balance["total"] += total

        free_val = bal.value_asset.format(bal.free_value)
        used_val = bal.value_asset.format(bal.used_value)
        total_val = bal.value_asset.format(bal.total_value)
        balance["free_value"] += free_val
        balance["used_value"] += used_val
        balance["total_value"] += total_val

    return balance


def get_inventory(user: core.db.User):
    sync_balances(user)

    balances = []
    inv_free_val = inv_used_val = inv_total_val = 0

    for asset in core.db.Asset.select():
        balance = get_balance_by_asset(user, asset)
        balances.append(balance)
        inv_free_val += balance["free_value"]
        inv_used_val += balance["used_value"]
        inv_total_val += balance["total_value"]

    inventory = {}
    inventory["balances"] = sorted(balances,
                                   key=lambda k: k["total_value"],
                                   reverse=True)
    inventory["free_value"] = inv_free_val
    inventory["used_value"] = inv_used_val
    inventory["total_value"] = inv_total_val

    inventory["positions_reserved"] = 0
    inventory["positions_value"] = 0
    for pos in user.get_open_positions():
        pos_asset = pos.user_strategy.strategy.market.quote
        # TODO positions_reserved could be other than USDT
        inventory["positions_reserved"] += pos_asset.format(pos.target_cost)
        inventory["positions_value"] += pos_asset.format(pos.entry_cost -
                                                         pos.exit_cost)

    inventory["net_liquid"] = \
        inventory["total_value"] - inventory["positions_reserved"]

    inventory["max_risk"] = inventory["net_liquid"] * user.max_risk

    return inventory


def get_target_cost(user_strat: core.db.UserStrategy):
    user = user_strat.user
    # each exchange has a target_cost
    exchange = user_strat.strategy.market.base.exchange
    print = user_strat.strategy.market.quote.print
    transform = user_strat.strategy.market.quote.transform

    inventory = get_inventory(user)

    # TODO currently, quote can only be USDT
    available_in_exch = user \
        .get_balances_by_asset(user_strat.strategy.market.quote.asset) \
        .where(core.db.ExchangeAsset.exchange == exchange) \
        .get_or_none()
    if not available_in_exch:
        available_in_exch = 0
    else:
        cash_in_exch = available_in_exch.total
    i("available {a} in exchange {e} is {v}"
      .format(a=user_strat.strategy.market.quote.asset.ticker,
              e=exchange.name,
              v=print(cash_in_exch)))

    available = cash_in_exch * (1 - user.cash_reserve)
    i("available minus reserve is {v}".format(v=print(available)))

    active_strat_in_exch = user.get_exchange_strategies(exchange).count()
    pos_curr_cost = [p.entry_cost for p in
                     user.get_exchange_open_positions(exchange)]
    available = (available + sum(pos_curr_cost)) / active_strat_in_exch
    i("available for strategy is {v}".format(v=print(available)))

    max_risk = transform(inventory["max_risk"])
    target_cost = min(max_risk, available)
    i("max risk is {v}".format(v=print(max_risk)))
    i("target cost is {v}".format(v=print(target_cost)))

    return int(target_cost)


# def refresh_targets(user):
#   this method will update target costs based on new risk parameters
#   it will effectively deleverage by reducing open positions to fit new params


def sync_balance(cred: core.db.Credential):
    value_ticker = "USDT"
    value_asset, new = core.db.Asset.get_or_create(ticker=value_ticker)
    if new:
        i("saved asset {a}".format(a=value_asset.ticker))

    try:
        ex_bal = core.exchange.api.fetch_balance()
    except ccxt.ExchangeError as e:
        core.watchdog.error("exchange error", e)
        cred.disable()
        return

    ex_val_asset, new = core.db.ExchangeAsset.get_or_create(
        exchange=cred.exchange, asset=value_asset)
    if new:
        i("saved asset {a} to exchange".format(a=ex_val_asset.asset.ticker))

    # for each exchange asset, update internal user balance
    for ticker in ex_bal["free"]:
        free = ex_bal["free"][ticker]
        used = ex_bal["used"][ticker]
        total = ex_bal["total"][ticker]

        if not total:
            continue

        asset, new = core.db.Asset.get_or_create(ticker=ticker.upper())
        if new:
            i("saved new asset {a}".format(a=asset.ticker))

        ex_asset, new = core.db.ExchangeAsset.get_or_create(
            exchange=cred.exchange, asset=asset)
        if new:
            i("saved asset {a}".format(a=ex_asset.asset.ticker))

        u_bal, new = core.db.Balance.get_or_create(
            user=cred.user, asset=ex_asset, value_asset=ex_val_asset)
        if new:
            i("saved new balance {b}".format(b=u_bal.id))

        u_bal.free = ex_asset.transform(free) if free else 0
        u_bal.used = ex_asset.transform(used) if used else 0
        u_bal.total = ex_asset.transform(total) if total else 0

        try:
            p = core.exchange.api.fetch_ticker(asset.ticker + "/" +
                                               value_asset.ticker)

            free_value = (ex_val_asset.transform(p["last"] * free)
                          if free else 0)
            used_value = (ex_val_asset.transform(p["last"] * used)
                          if used else 0)
            total_value = (ex_val_asset.transform(p["last"] * total)
                           if total else 0)

        except ccxt.BadSymbol:
            try:
                p = core.exchange.api.fetch_ticker(value_asset.ticker + "/" +
                                                   asset.ticker)

                free_value = (ex_val_asset.transform(free / p["last"])
                              if free else 0)
                used_value = (ex_val_asset.transform(used / p["last"])
                              if used else 0)
                total_value = (ex_val_asset.transform(total / p["last"])
                               if total else 0)
            except ccxt.BadSymbol:
                free_value = u_bal.free
                used_value = u_bal.used
                total_value = u_bal.total

        u_bal.free_value = free_value
        u_bal.used_value = used_value
        u_bal.total_value = total_value

        u_bal.save()


def sync_balances(user: core.db.User):
    active_exchanges = []
    # sync balance for each exchange the user has a key
    for cred in user.credential_set.where(core.db.Credential.active):
        i("fetching user balance in exchange {e}".format(e=cred.exchange.name))
        core.exchange.set_api(cred=cred)
        sync_balance(cred)
        active_exchanges.append(cred.exchange)

    # delete inactive balances
    for bal in user.balance_set:
        if bal.asset.exchange not in active_exchanges:
            bal.delete_instance()
