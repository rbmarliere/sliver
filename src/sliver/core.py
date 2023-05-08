import argparse

import peewee
import waitress

from sliver.asset import Asset
from sliver.trade_engine import TradeEngine
from sliver.price import Price
from sliver.exchange import Exchange
from sliver.market import Market
from sliver.exchange_asset import ExchangeAsset
from sliver.credential import Credential
from sliver.balance import Balance
from sliver.indicator import Indicator
from sliver.strategy import BaseStrategy
from sliver.user_strategy import UserStrategy
from sliver.user import User
from sliver.order import Order
from sliver.position import Position

from sliver.database import db_init
from sliver.watchdog import Watchdog
from sliver.config import Config

from sliver.api.app import api

__all__ = [
    "Asset",
    "TradeEngine",
    "Price",
    "Exchange",
    "Market",
    "ExchangeAsset",
    "Credential",
    "Balance",
    "Indicator",
    "BaseStrategy",
    "UserStrategy",
    "User",
    "Order",
    "Position",
]


def create_tables(connection):
    connection.create_tables(
        [
            Asset,
            TradeEngine,
            Price,
            Exchange,
            Market,
            ExchangeAsset,
            Credential,
            Balance,
            Indicator,
            BaseStrategy,
            UserStrategy,
            User,
            Order,
            Position,
        ],
        safe=True,
    )
    try:
        TradeEngine._schema.create_foreign_key(TradeEngine.creator)
        Price._schema.create_foreign_key(Price.market)
        Credential._schema.create_foreign_key(Credential.user)
        Balance._schema.create_foreign_key(Balance.user)
        Indicator._schema.create_foreign_key(Indicator.strategy)
        BaseStrategy._schema.create_foreign_key(BaseStrategy.creator)
        UserStrategy._schema.create_foreign_key(UserStrategy.user)
        Order._schema.create_foreign_key(Order.position)
    except peewee.ProgrammingError:
        pass


def watch(num_workers=1):
    argp = argparse.ArgumentParser()
    argp.add_argument("num_workers", nargs="?", type=int, default=num_workers)
    args = argp.parse_args()
    Watchdog(num_workers=args.num_workers).run()


def serve():
    db_init()

    if Config().ENV_NAME == "development":
        api.app.run(port=5000, debug=False)

    elif Config().ENV_NAME == "production":
        waitress.serve(api.app, port=5000, channel_timeout=360)
