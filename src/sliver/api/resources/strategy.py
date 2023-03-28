import datetime

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, marshal

import sliver.database as db
from sliver.api.exceptions import (
    InvalidArgument,
    MarketAlreadySubscribed,
    StrategyDoesNotExist,
    StrategyIsActive,
    StrategyNotEditable,
)
from sliver.api.resources.fields import (
    get_activation_parser,
    get_base_parser,
    get_fields,
    get_subscription_parser,
)
from sliver.exceptions import MarketAlreadySubscribed as BaseMarketAlreadySubscribed
from sliver.indicator import Indicator
from sliver.strategies.factory import StrategyFactory
from sliver.strategies.mixer import MixedStrategies
from sliver.strategies.types import StrategyTypes
from sliver.strategy import BaseStrategy as StrategyModel
from sliver.user import User
from sliver.user_strategy import UserStrategy


class Strategy(Resource):
    @jwt_required()
    def get(self, strategy_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            strategy = StrategyModel.get_by_id(strategy_id)
            if strategy.deleted:
                raise StrategyDoesNotExist
        except StrategyModel.DoesNotExist:
            raise StrategyDoesNotExist

        strategy = StrategyFactory.from_base(strategy)
        strategy.subscribed = user.is_subscribed(strategy.id)

        return marshal(strategy, get_fields(strategy.type))

    @jwt_required()
    def delete(self, strategy_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            strategy = StrategyModel.get_by_id(strategy_id)
            if strategy.deleted:
                raise StrategyDoesNotExist
            if strategy.creator != user:
                raise StrategyNotEditable
            if UserStrategy.get_active_strategy(strategy).count() > 0:
                raise StrategyIsActive
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

        if old_strategy.deleted:
            raise StrategyDoesNotExist

        try:
            args = get_subscription_parser().parse_args()
            if args["subscribe"]:
                UserStrategy.subscribe(
                    user, old_strategy, subscribed=args["subscribed"]
                )

                strategy = StrategyFactory.from_base(old_strategy)
                strategy.subscribed = user.is_subscribed(strategy.id)

                return marshal(strategy, get_fields(strategy.type))
        except BaseMarketAlreadySubscribed:
            raise MarketAlreadySubscribed
        except KeyError:
            pass

        try:
            args = get_activation_parser().parse_args()
            if args["activate"]:
                if args["active"]:
                    old_strategy.enable()
                else:
                    old_strategy.disable()

                strategy = StrategyFactory.from_base(old_strategy)
                strategy.subscribed = user.is_subscribed(strategy.id)

                return marshal(strategy, get_fields(strategy.type))
        except BaseMarketAlreadySubscribed:
            raise MarketAlreadySubscribed
        except KeyError:
            pass

        args = get_base_parser(old_strategy.type).parse_args()

        if old_strategy.creator != user:
            raise StrategyNotEditable

        with db.connection.atomic():
            args["id"] = int(strategy_id)
            args["market"] = old_strategy.market.id
            args["timeframe"] = old_strategy.timeframe
            args["type"] = old_strategy.type
            args["active"] = old_strategy.active
            args["next_refresh"] = datetime.datetime.utcnow()

            strategy = StrategyModel(**args)
            strategy.save()

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

            strategy = StrategyFactory.from_base(strategy)

            for field in strategy._meta.sorted_field_names:
                try:
                    if args[field] is not None:
                        setattr(strategy, field, args[field])
                except KeyError:
                    pass

            strategy.save()

            Indicator.delete().where(Indicator.strategy_id == strategy_id).execute()

        strategy = StrategyFactory.from_base(strategy)
        strategy.subscribed = user.is_subscribed(strategy.id)

        return marshal(strategy, get_fields(strategy.type))
