import peewee
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, marshal_with

import api
import core
import strategies
from api.resources.fields.strategy import base_fields, get_base_parser


class Strategies(Resource):
    @marshal_with(base_fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        strat_list = []
        for strategy in [s for s in core.db.get_strategies()]:
            strat_list.append(strategies.load(strategy, user=user))

        return strat_list

    @marshal_with(base_fields)
    @jwt_required()
    def post(self):
        args = get_base_parser().parse_args()

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        with core.db.connection.atomic():
            try:
                args["id"] = None
                args["active"] = True
                args["creator"] = user
                strategy = core.db.Strategy.create(**args)
                strategy.save()

                strategy = strategies.load(strategy, user=user)
            except (peewee.IntegrityError, core.db.Market.DoesNotExist):
                raise api.errors.InvalidArgument

        return strategy


class StrategiesByMarket(Resource):
    @marshal_with(base_fields)
    @jwt_required()
    def get(self, market_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        strat_list = []
        for strategy in [s for s in core.db.get_strategies()]:
            if strategy.market_id == int(market_id) \
                    and strategy.type != strategies.Types.MIXER.value \
                    and strategy.type != strategies.Types.MANUAL.value:
                strat_list.append(strategies.load(strategy, user=user))

        return strat_list
