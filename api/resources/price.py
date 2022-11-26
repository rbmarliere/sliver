from flask_jwt_extended import jwt_required
from flask_restful import Resource, fields, marshal_with

import api
import core

fields = {
    "time": fields.List(fields.String),
    "open": fields.List(fields.Float),
    "high": fields.List(fields.Float),
    "low": fields.List(fields.Float),
    "close": fields.List(fields.Float),
    "volume": fields.List(fields.Float),
    "signal": fields.List(fields.String),
    "i_score": fields.List(fields.Float),
    "p_score": fields.List(fields.Float),
    "buys": fields.List(fields.Float),
    "sells": fields.List(fields.Float),
    "backtest_log": fields.String
}


class Price(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, strategy_id):
        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        return core.strategy.backtest(strategy)
