import peewee
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, marshal_with

import api
import core
import strategies
from api.resources.fields.strategy import base_fields, get_parser


class Strategies(Resource):
    @marshal_with(base_fields)
    @jwt_required()
    def get(self):
        strat_list = [s for s in
                      core.db.Strategy.select()
                      .where(core.db.Strategy.deleted == False)
                      .order_by(core.db.Strategy.id.desc())]
        for strategy in strat_list:
            strategy.symbol = strategy.market.get_symbol()
            strategy.exchange = strategy.market.quote.exchange.name

        return strat_list

    @marshal_with(base_fields)
    @jwt_required()
    def post(self):
        args = get_parser().parse_args()

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        with core.db.connection.atomic():
            try:
                args["id"] = None
                args["active"] = True
                args["creator"] = user
                args["stop_loss"] = abs(args.stop_loss)
                args["min_roi"] = abs(args.min_roi)
                strategy = core.db.Strategy.create(**args)
                strategy.save()

                strategies.load(strategy)
            except (peewee.IntegrityError, core.db.Market.DoesNotExist):
                raise api.errors.InvalidArgument

        strategy.symbol = strategy.market.get_symbol()
        strategy.exchange = strategy.market.quote.exchange.name

        return strategy
