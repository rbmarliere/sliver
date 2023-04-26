import peewee
from flask_jwt_extended import jwt_required
from flask_restful import Resource, marshal

from sliver.api.exceptions import StrategyDoesNotExist
from sliver.strategies.factory import StrategyFactory
from sliver.strategy import BaseStrategy


class Indicator(Resource):
    @jwt_required()
    def get(self, strategy_id):
        try:
            strategy = StrategyFactory.from_base(BaseStrategy.get_by_id(strategy_id))
            if strategy.deleted:
                raise StrategyDoesNotExist
        except BaseStrategy.DoesNotExist:
            raise StrategyDoesNotExist

        ind = strategy.get_indicators_df(join_type=peewee.JOIN.INNER)

        if not ind.empty:
            ind.replace({float("nan"): None}, inplace=True)

        return marshal(ind.to_dict("list"), strategy.get_indicator_fields())
