import argparse
import sys

import sliver.database as db
from sliver.exchanges.factory import ExchangeFactory
from sliver.position import Position

if __name__ == "__main__":
    db.init()

    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-o", "--order_id", type=str, help="Exchange Order ID", required=True
    )
    argp.add_argument(
        "-p", "--position_id", help="position id to update all orders", required=True
    )
    args = argp.parse_args()

    try:
        pos = Position.get_by_id(args.position_id)
    except Position.DoesNotExist:
        print("position not found")
        sys.exit(1)

    market = pos.user_strategy.strategy.market
    exchange = market.quote.exchange
    cred = pos.user_strategy.user.get_active_credential(exchange).get()
    exchange = ExchangeFactory.from_credential(cred)

    order = exchange.get_synced_order(pos, args.order_id)

    if order.status == "closed":
        pos.add_order(order)
