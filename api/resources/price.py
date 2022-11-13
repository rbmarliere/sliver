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
    "p_score": fields.Float
}


class Price(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, strategy_id):
        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        prices = core.strategy.get_prices(strategy)
        indicators = core.strategy.get_indicators(strategy, prices).to_dict("records")

        return indicators
