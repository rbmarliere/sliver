import waitress
import peewee

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
from sliver.user import User
from sliver.user_strategy import UserStrategy
from sliver.order import Order
from sliver.position import Position

from sliver.database import connection
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


def create_tables():
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
        Price._schema.create_foreign_key(Price.market)
        Credential._schema.create_foreign_key(Credential.user)
        Balance._schema.create_foreign_key(Balance.user)
        Indicator._schema.create_foreign_key(Indicator.strategy)
        BaseStrategy._schema.create_foreign_key(BaseStrategy.creator)
        UserStrategy._schema.create_foreign_key(UserStrategy.user)
        Order._schema.create_foreign_key(Order.position)
    except peewee.ProgrammingError:
        pass


def watch():
    create_tables()
    Watchdog().run_loop()


def serve():
    create_tables()

    Watchdog().logger = "api"

    if Config().ENV_NAME == "development":
        api.app.run(port=5000, debug=False)

    elif Config().ENV_NAME == "production":
        waitress.serve(api.app, port=5000)
