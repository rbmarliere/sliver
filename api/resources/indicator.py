from flask_jwt_extended import jwt_required
from flask_restful import Resource, marshal

import api
import core
import strategies
from api.resources.fields.strategy import get_fields


class Indicator(Resource):
    @jwt_required()
    def get(self, strategy_id):
        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
            if strategy.deleted:
                raise api.errors.StrategyDoesNotExist
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        strategy = strategies.load(strategy)
        strategy.refresh_indicators()

        ind = strategy.get_indicators_df()

        return marshal(ind.to_dict("list"),
                       get_fields(strategy.type, all=False))
