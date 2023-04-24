import argparse
import sys

from sliver.core import Position

from sliver.exchanges.factory import ExchangeFactory

if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-p", "--position_id", help="position id to update all orders", required=True
    )
    argp.add_argument(
        "-f",
        "--fetch-orders",
        help="fetch orders from exchange before updating",
        action="store_true",
    )
    args = argp.parse_args()

    try:
        pos = Position.get_by_id(args.position_id)
    except Position.DoesNotExist:
        print("position not found")
        sys.exit(1)

    pos.entry_cost = 0
    pos.entry_amount = 0
    pos.entry_price = 0
    pos.exit_price = 0
    pos.exit_amount = 0
    pos.exit_cost = 0
    pos.fee = 0

    market = pos.user_strategy.strategy.market
    base = market.quote.exchange
    cred = pos.user_strategy.user.get_active_credential(base).get()
    exchange = ExchangeFactory.from_credential(cred)

    for order in pos.get_orders():
        if args.fetch_orders:
            order = exchange.get_synced_order(pos, order.exchange_order_id)
        if order.status != "open":
            pos.add_order(order)

    if pos.status == "closed":
        pos.pnl = pos.get_pnl()
        pos.roi = pos.get_roi()

    pos.save()
