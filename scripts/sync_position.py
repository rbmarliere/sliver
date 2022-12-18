#!/usr/bin/env python3

import argparse
import sys

import core

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-p",
                      "--position_id",
                      help="position id to update all orders",
                      required=True)
    argp.add_argument("-f",
                      "--fetch-orders",
                      help="fetch orders from exchange before updating",
                      action="store_true")
    args = argp.parse_args()

    try:
        pos = core.db.Position.get_by_id(args.position_id)
    except core.db.Position.DoesNotExist:
        print("position not found")
        sys.exit(1)

    pos.entry_cost = 0
    pos.entry_amount = 0
    pos.entry_price = 0
    pos.exit_price = 0
    pos.exit_amount = 0
    pos.exit_cost = 0
    pos.fee = 0
    exchange = pos.user_strategy.strategy.market.quote.exchange
    cred = pos.user_strategy.user.get_active_credential(exchange).get()
    for order in pos.get_orders():
        if args.fetch_orders:
            core.exchange.set_api(cred=cred)
            ex_order = core.exchange.api.fetch_order(order.exchange_order_id)

            order.sync(ex_order, pos)
        elif order.status != "open":
            pos.add_order(order)

    if pos.status == "closed":
        pos.pnl = (pos.exit_cost - pos.entry_cost - pos.fee)

    pos.save()
