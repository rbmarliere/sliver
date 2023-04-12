from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, marshal_with
from peewee import IntegrityError

import sliver.database as db
from sliver.api.exceptions import InvalidArgument
from sliver.api.resources.fields import base_fields, get_base_parser
from sliver.market import Market
from sliver.strategies.factory import StrategyFactory
from sliver.strategies.types import StrategyTypes
from sliver.strategy import BaseStrategy as Strategy
from sliver.user import User


class Strategies(Resource):
    @marshal_with(base_fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        strat_list = []
        for s in Strategy.get_existing():
            s.subscribed = user.is_subscribed(s.id)
            s.signal = s.get_signal()
            strat_list.append(s)

        return strat_list

    @marshal_with(base_fields)
    @jwt_required()
    def post(self):
        args = get_base_parser().parse_args()

        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        with db.connection.atomic():
            try:
                args["id"] = None
                args["active"] = True
                args["creator"] = user
                strategy = Strategy.create(**args)
                strategy.save()
            except (IntegrityError, Market.DoesNotExist):
                raise InvalidArgument

            strategy = StrategyFactory.from_base(strategy)

        return strategy


class StrategiesByMarket(Resource):
    @marshal_with(base_fields)
    @jwt_required()
    def get(self, market_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        strat_list = []
        for strategy in [s for s in Strategy.get_existing()]:
            if (
                strategy.market_id == int(market_id)
                and strategy.type != StrategyTypes.MIXER
                and strategy.type != StrategyTypes.MANUAL
            ):
                strategy.subscribed = user.is_subscribed(strategy.id)
                strat_list.append(strategy)

        return strat_list
