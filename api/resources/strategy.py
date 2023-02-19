import datetime

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, marshal

import api
import core
import strategies
from api.resources.fields.strategy import (get_fields,
                                           get_base_parser,
                                           get_subscription_parser,
                                           get_activation_parser)


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

        try:
            args = get_subscription_parser().parse_args()
            if args["subscribe"]:
                old_strategy.subscribe(user, args["subscribed"])
                strategy = strategies.load(old_strategy, user=user)
                return marshal(strategy, get_fields(strategy.type))
        except core.errors.MarketAlreadySubscribed:
            raise api.errors.MarketAlreadySubscribed
        except KeyError:
            pass

        try:
            args = get_activation_parser().parse_args()
            if args["activate"]:
                if args["active"]:
                    old_strategy.enable()
                else:
                    old_strategy.disable()
                strategy = strategies.load(old_strategy, user=user)
                return marshal(strategy, get_fields(strategy.type))
        except core.errors.MarketAlreadySubscribed:
            raise api.errors.MarketAlreadySubscribed
        except KeyError:
            pass

        args = get_base_parser(old_strategy.type).parse_args()

        if old_strategy.creator != user:
            raise api.errors.StrategyNotEditable

        with core.db.connection.atomic():
            args["id"] = int(strategy_id)
            args["market"] = old_strategy.market.id
            args["timeframe"] = old_strategy.timeframe
            args["type"] = old_strategy.type
            args["active"] = old_strategy.active
            # force instant strat update
            args["next_refresh"] = datetime.datetime.utcnow()
            strategy = core.db.Strategy(**args)
            strategy.save()

            if strategy.type == strategies.Types.MIXER.value:
                mixin = strategies.mixer.MixedStrategies
                mixin.delete() \
                    .where(mixin.mixer_id == strategy_id) \
                    .execute()

                if args["strategies"] \
                        and args["buy_weights"] and args["sell_weights"]:
                    if len(args["strategies"]) != len(args["buy_weights"]):
                        raise api.errors.InvalidArgument
                    if len(args["strategies"]) != len(args["sell_weights"]):
                        raise api.errors.InvalidArgument

                    if len(args["strategies"]) != len(set(args["strategies"])):
                        raise api.errors.InvalidArgument(
                            "Mixed strategies must be unique")

                    for s, b_w, s_w in zip(args["strategies"],
                                           args["buy_weights"],
                                           args["sell_weights"]):
                        mixed_st = core.db.Strategy.get_by_id(s)

                        if mixed_st.deleted:
                            raise api.errors.StrategyDoesNotExist
                        if mixed_st.timeframe != strategy.timeframe:
                            raise api.errors.InvalidArgument(
                                "Mixed strategies must have same timeframe")
                        if mixed_st.market != strategy.market:
                            raise api.errors.InvalidArgument(
                                "Mixed strategies must have same market")
                        if mixed_st.type == strategies.Types.MIXER.value:
                            raise api.errors.InvalidArgument(
                                "Mixed strategies cannot be of type MIXER")
                        if mixed_st.type == strategies.Types.MANUAL.value:
                            raise api.errors.InvalidArgument(
                                "Mixed strategies cannot be of type MANUAL")

                        mixed_st.enable()
                        mixin.create(
                            mixer_id=strategy_id,
                            strategy_id=mixed_st.id,
                            buy_weight=b_w,
                            sell_weight=s_w)

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

        strategy = strategies.load(core.db.Strategy.get_by_id(strategy_id),
                                   user=user)

        return marshal(strategy, get_fields(strategy.type))
