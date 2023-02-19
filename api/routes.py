import flask_restful

import api.resources as resources
from .auth import Auth


def init(api: flask_restful.Api):
    api.add_resource(Auth, "/login")
    api.add_resource(resources.Credential, "/credentials")
    api.add_resource(resources.Engine, "/engine/<engine_id>")
    api.add_resource(resources.Engines, "/engines")
    api.add_resource(resources.Exchange, "/exchanges")
    api.add_resource(resources.Indicator, "/indicators/<strategy_id>")
    api.add_resource(resources.Inventory, "/inventory")
    api.add_resource(resources.Order, "/orders/<position_id>")
    api.add_resource(resources.Position, "/positions")
    api.add_resource(resources.PositionsByStrategy,
                     "/positions/strategy/<strategy_id>")
    api.add_resource(resources.Strategies, "/strategies")
    api.add_resource(resources.StrategiesByMarket,
                     "/strategies/market/<market_id>")
    api.add_resource(resources.StrategiesByTimeframe,
                     "/strategies/timeframe/<timeframe>")
    api.add_resource(resources.Strategy, "/strategy/<strategy_id>")
    api.add_resource(resources.User, "/user")
