import peewee
from flask_jwt_extended import jwt_required
from flask_restful import Resource, fields, marshal_with

import api
import core

fields = {
    "time": fields.DateTime,
    "open": fields.String,
    "high": fields.String,
    "low": fields.String,
    "close": fields.String,
    "volume": fields.String,
    "signal": fields.String,
    "i_score": fields.Float,
    "p_score": fields.Float,
}


class Price(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, strategy_id):
        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        q = strategy\
            .get_prices() \
            .join(core.db.Indicator, peewee.JOIN.LEFT_OUTER) \
            .select(core.db.Price, core.db.Indicator) \
            .order_by(core.db.Price.id)

        return [p for p in q.dicts()]
