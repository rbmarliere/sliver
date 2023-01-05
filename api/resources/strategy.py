from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, marshal

import api
import core
import strategies
from api.resources.fields.strategy import get_fields, get_parser


class Strategy(Resource):
    @jwt_required()
    def get(self, strategy_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
            if strategy.deleted:
                raise api.errors.StrategyDoesNotExist
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        strategy = strategies.load(strategy, user=user)
        strategy.refresh_indicators()

        ind = strategy.get_indicators_df()
        strategy.prices = ind.to_dict("list")

        return marshal(strategy, get_fields(strategy.type))

    @jwt_required()
    def delete(self, strategy_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
            if strategy.deleted:
                raise api.errors.StrategyDoesNotExist
            if strategy.creator != user:
                raise api.errors.StrategyNotEditable
            if strategy.get_active_users().count() > 0:
                raise api.errors.StrategyIsActive
            strategy.delete()
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        return "", 204

    @jwt_required()
    def put(self, strategy_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            old_strategy = core.db.Strategy.get_by_id(strategy_id)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        if old_strategy.deleted:
            raise api.errors.StrategyDoesNotExist

        args = get_parser(old_strategy.type).parse_args()

        try:
            if args["subscribe"]:
                old_strategy.subscribe(user, args["subscribed"])
                strategy = strategies.load(old_strategy, user=user)
                return marshal(strategy, get_fields(strategy.type))
        except core.errors.MarketAlreadySubscribed:
            raise api.errors.MarketAlreadySubscribed
        except KeyError:
            pass

        if old_strategy.creator != user:
            raise api.errors.StrategyNotEditable

        with core.db.connection.atomic():
            args["id"] = int(strategy_id)
            if args["stop_loss"]:
                args["stop_loss"] = abs(args.stop_loss)
            if args["stop_gain"]:
                args["stop_gain"] = abs(args.stop_gain)
            args["market"] = old_strategy.market.id
            args["type"] = old_strategy.type
            strategy = core.db.Strategy(**args)
            strategy.save()

            strategy = strategies.load(strategy)
            if len([*strategy._meta.columns]) > 1:
                for field in strategy._meta.sorted_field_names:
                    try:
                        if args[field] is not None:
                            setattr(strategy, field, args[field])
                    except KeyError:
                        pass
                strategy.save()

            core.db.Indicator \
                .delete() \
                .where(core.db.Indicator.strategy_id == strategy_id) \
                .execute()

        strategy = strategies.load(strategy, user=user)

        return marshal(strategy, get_fields(strategy.type))
