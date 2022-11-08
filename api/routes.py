import flask_restful

import api.resources as resources

from .auth import Auth


def init(api: flask_restful.Api):
    api.add_resource(Auth, "/login")
    api.add_resource(resources.Credential, "/credentials/<exchange_id>")
    api.add_resource(resources.Exchange, "/exchanges")
    api.add_resource(resources.Inventory, "/inventory")
    api.add_resource(resources.Order, "/orders/<position_id>")
    api.add_resource(resources.Position, "/positions")
    api.add_resource(resources.Strategy, "/strategies")
    api.add_resource(resources.User, "/user")
