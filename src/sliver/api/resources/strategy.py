import datetime

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, marshal, reqparse

import sliver.database as db
from sliver.api.exceptions import (
    InvalidArgument,
    StrategyDoesNotExist,
    StrategyIsActive,
    StrategyMixedIn,
    StrategyNotEditable,
    StrategyRefreshing,
)
from sliver.position import Position
from sliver.strategies.factory import StrategyFactory, StrategyTypes
from sliver.strategies.mixer import MixedStrategies
from sliver.strategies.status import StrategyStatus
from sliver.strategy import BaseStrategy as StrategyModel
from sliver.user import User
from sliver.user_strategy import UserStrategy


def get_subscription_parser():
    parser = reqparse.RequestParser()
    parser.add_argument("subscribe", type=bool, required=False)
    parser.add_argument("subscribed", type=bool, required=False)
    return parser


def get_activation_parser():
    parser = reqparse.RequestParser()
    parser.add_argument("activate", type=bool, required=False)
    parser.add_argument("active", type=bool, required=False)
    return parser


class Strategy(Resource):
    @jwt_required()
    def get(self, strategy_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            strategy = StrategyModel.get_by_id(strategy_id)
            if strategy.is_deleted():
                raise StrategyDoesNotExist
        except StrategyModel.DoesNotExist:
            raise StrategyDoesNotExist

        parser = reqparse.RequestParser()
        parser.add_argument(
            "active", type=lambda x: x.lower() == "true", default=None, location="args"
        )
        parser.add_argument(
            "subscribe",
            type=lambda x: x.lower() == "true",
            default=None,
            location="args",
        )
        args = parser.parse_args()

        if args.active is not None:
            if args.active:
                strategy.enable()
            else:
                strategy.disable()

        if args.subscribe is not None:
            UserStrategy.subscribe(user, strategy, subscribed=args.subscribe)
            if args.subscribe:
                strategy.next_refresh = datetime.datetime.utcnow()
                strategy.save()

        strategy = StrategyFactory.from_base(strategy)
        strategy.subscribed = user.is_subscribed(strategy.id)
        strategy.signal = strategy.get_signal()

        if strategy.type == StrategyTypes.MIXER:
            strategy.mixins = [
                {
                    "strategy_id": m.strategy_id,
                    "buy_weight": m.buy_weight,
                    "sell_weight": m.sell_weight,
                }
                for m in strategy.mixins
            ]

        return marshal(strategy, strategy.get_fields())

    @jwt_required()
    def delete(self, strategy_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            strategy = StrategyModel.get_by_id(strategy_id)
            if strategy.is_deleted():
                raise StrategyDoesNotExist
            if strategy.creator != user and user.id != 1:
                raise StrategyNotEditable
            if strategy.userstrategy_set.count() > 0:
                raise StrategyIsActive
            if strategy.mixedstrategies_set.count() > 0:
                raise StrategyMixedIn

            strategy.delete()
        except StrategyModel.DoesNotExist:
            raise StrategyDoesNotExist

        return "", 204

    @jwt_required()
    def put(self, strategy_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            old_strategy = StrategyModel.get_by_id(strategy_id)
        except StrategyModel.DoesNotExist:
            raise StrategyDoesNotExist

        if old_strategy.is_deleted():
            raise StrategyDoesNotExist

        if old_strategy.creator != user and user.id != 1:
            raise StrategyNotEditable

        if old_strategy.is_refreshing():
            raise StrategyRefreshing

        strategy = StrategyFactory.from_base(old_strategy)

        args = strategy.get_parser().parse_args()

        with db.connection.atomic():
            args["id"] = int(strategy_id)
            args["market"] = old_strategy.market.id
            args["timeframe"] = old_strategy.timeframe
            args["type"] = old_strategy.type
            args["status"] = StrategyStatus.IDLE
            args["reset"] = True
            args["next_refresh"] = datetime.datetime.utcnow()

            if (
                args["buy_engine_id"] != old_strategy.buy_engine_id
                or args["sell_engine_id"] != old_strategy.sell_engine_id
                or args["stop_engine_id"] != old_strategy.stop_engine_id
            ):
                for p in Position.get_open().where(StrategyModel.id == strategy_id):
                    p.next_refresh = datetime.datetime.utcnow()
                    p.save()

            new_strategy = StrategyModel(**args)
            new_strategy.save()

            if strategy.type == StrategyTypes.MIXER:
                mixin = MixedStrategies
                mixin.delete().where(mixin.mixer_id == strategy_id).execute()

                if args["strategies"] and args["buy_weights"] and args["sell_weights"]:
                    if len(args["strategies"]) != len(args["buy_weights"]):
                        raise InvalidArgument
                    if len(args["strategies"]) != len(args["sell_weights"]):
                        raise InvalidArgument

                    if len(args["strategies"]) != len(set(args["strategies"])):
                        raise InvalidArgument("Mixed strategies must be unique")

                    for s, b_w, s_w in zip(
                        args["strategies"], args["buy_weights"], args["sell_weights"]
                    ):
                        mixed_st = StrategyModel.get_by_id(s)

                        if mixed_st.deleted:
                            raise StrategyDoesNotExist
                        if mixed_st.market != strategy.market:
                            raise InvalidArgument(
                                "Mixed strategies must have same market"
                            )
                        if mixed_st.type == StrategyTypes.MIXER:
                            raise InvalidArgument(
                                "Mixed strategies cannot be of type MIXER"
                            )
                        if mixed_st.type == StrategyTypes.MANUAL:
                            raise InvalidArgument(
                                "Mixed strategies cannot be of type MANUAL"
                            )

                        mixed_st.enable()
                        mixin.create(
                            mixer_id=strategy_id,
                            strategy_id=mixed_st.id,
                            buy_weight=b_w,
                            sell_weight=s_w,
                        )

            strategy = StrategyFactory.from_base(new_strategy)

            for field in strategy._meta.sorted_field_names:
                try:
                    if args[field] is not None:
                        setattr(strategy, field, args[field])
                except KeyError:
                    pass

            try:
                strategy.save()
            except ValueError:
                pass

        strategy.subscribed = user.is_subscribed(strategy.id)
        strategy.signal = strategy.get_signal()

        return marshal(strategy, strategy.get_fields())
