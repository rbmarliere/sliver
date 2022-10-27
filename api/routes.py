import flask_restful

from .auth import Auth
from api.resources.strategy import Strategy


def init(api: flask_restful.Api):
    api.add_resource(Auth, "/login")
    api.add_resource(Strategy, "/strategies")
