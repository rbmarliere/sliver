import flask_restful

from . import resources
from .auth import Auth


def init(api: flask_restful.Api):
    api.add_resource(Auth, "/login")
    api.add_resource(resources.Credential, "/credentials")
    api.add_resource(resources.Engine, "/engine/<engine_id>")
    api.add_resource(resources.Engines, "/engines")
    api.add_resource(resources.Exchange, "/exchanges")
    api.add_resource(resources.Indicator, "/indicators/<strategy_id>")
    api.add_resource(resources.Inventory, "/inventory")
    api.add_resource(resources.Order, "/order/<order_id>")
    api.add_resource(resources.Orders, "/orders/<position_id>")
    api.add_resource(resources.Position, "/position/<position_id>")
    api.add_resource(resources.Positions, "/positions")
    api.add_resource(resources.PositionsByStrategy, "/positions/strategy/<strategy_id>")
    api.add_resource(resources.Strategies, "/strategies")
    api.add_resource(resources.StrategiesByMarket, "/strategies/market/<market_id>")
    api.add_resource(resources.Strategy, "/strategy/<strategy_id>")
    api.add_resource(resources.User, "/user")
