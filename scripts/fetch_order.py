#!/usr/bin/env python3

import argparse
import sys

import ccxt

import core


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-o",
                      "--order_id",
                      type=str,
                      help="Exchange Order ID",
                      required=True)
    argp.add_argument("-p",
                      "--position_id",
                      help="position id to update all orders",
                      required=True)
    args = argp.parse_args()

    try:
        pos = core.db.Position.get_by_id(args.position_id)
    except core.db.Position.DoesNotExist:
        print("position not found")
        sys.exit(1)

    market = pos.user_strategy.strategy.market
    exchange = market.quote.exchange
    cred = pos.user_strategy.user.get_active_credential(exchange).get()
    core.exchange.set_api(cred=cred)

    try:
        ex_order = core.exchange.api.fetch_order(market.get_symbol(),
                                                 oid=args.order_id)

        order = core.db.Order.get_or_none(exchange_order_id=args.order_id)
        if order is None:
            order = core.db.Order()

        core.db.Order.sync(order,
                           ex_order,
                           pos)
    except ccxt.OrderNotFound:
        print("order not found")
        sys.exit(1)
    except ccxt.BaseError as e:
        print(e)
        sys.exit(1)
