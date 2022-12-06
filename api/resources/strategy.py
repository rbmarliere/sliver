import peewee
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with, reqparse, inputs

import api
import core

fields = {
    "symbol": fields.String,
    "market_id": fields.Integer,
    "id": fields.Integer,
    "subscribed": fields.Boolean,
    "active": fields.Boolean,
    "description": fields.String,
    "mode": fields.String,
    "timeframe": fields.String,
    "signal": fields.String,
    "refresh_interval": fields.Integer,
    "next_refresh": fields.DateTime(dt_format="iso8601"),
    "num_orders": fields.Integer,
    "bucket_interval": fields.Integer,
    "spread": fields.Float,
    "min_roi": fields.Float,
    "stop_loss": fields.Float,
    "i_threshold": fields.Float,
    "p_threshold": fields.Float,
    "tweet_filter": fields.String
}

argp = reqparse.RequestParser()
argp.add_argument("market_id", type=int)
argp.add_argument("id", type=int)
argp.add_argument("subscribed", type=bool)
argp.add_argument("active", type=bool)
argp.add_argument("description", type=str)
argp.add_argument("mode", type=str)
argp.add_argument("timeframe", type=str)
argp.add_argument("signal", type=str)
argp.add_argument("refresh_interval", type=int)
argp.add_argument("next_refresh", type=inputs.datetime_from_iso8601)
argp.add_argument("num_orders", type=int)
argp.add_argument("bucket_interval", type=int)
argp.add_argument("spread", type=float)
argp.add_argument("min_roi", type=float)
argp.add_argument("stop_loss", type=float)
argp.add_argument("i_threshold", type=float)
argp.add_argument("p_threshold", type=float)
argp.add_argument("tweet_filter", type=str)


class Strategy(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        strategies = [s for s in
                      core.db.Strategy.select()
                      .order_by(core.db.Strategy.id.asc())]

        for st in strategies:
            st.subscribed = user.is_subscribed(st)
            st.symbol = st.market.get_symbol()

        return strategies

    @marshal_with(fields)
    @jwt_required()
    def post(self):
        args = argp.parse_args()

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        if args.id and args.id > 0:
            return self.subscribe(args, user)
        else:
            return self.create(args, user)

    def subscribe(self, args, user):
        try:
            strategy = core.db.Strategy.get_by_id(args.id)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        user_strat_exists = False
        for u_st in user.userstrategy_set:
            if u_st.strategy == strategy:
                user_strat_exists = True
                u_st.active = args.subscribed
                u_st.save()

        if not user_strat_exists:
            core.db.UserStrategy(
                user=user, strategy=strategy, active=args.subscribed).save()

        strategy.subscribed = args.subscribed
        strategy.symbol = strategy.market.get_symbol()

        return strategy

    def create(self, args, user):
        strategy = core.db.Strategy(**args)
        strategy.id = None
        strategy.active = True
        strategy.user = user

        try:
            strategy.save()
        except (peewee.IntegrityError, core.db.Market.DoesNotExist):
            raise api.errors.InvalidArgument

        strategy.subscribed = False
        strategy.symbol = strategy.market.get_symbol()

        return strategy

    @marshal_with(fields)
    @jwt_required()
    def put(self):
        args = argp.parse_args()

        if not args.id:
            raise api.errors.InvalidArgument

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            old_strategy = core.db.Strategy.get_by_id(args.id)
            market = old_strategy.market
            if old_strategy.user != user:
                raise api.errors.StrategyNotEditable
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        strategy = core.db.Strategy(**args)
        strategy.market = market
        strategy.save()

        strategy.subscribed = user.is_subscribed(strategy)
        strategy.symbol = strategy.market.get_symbol()

        if (strategy.i_threshold != float(old_strategy.i_threshold)
                or strategy.p_threshold != float(old_strategy.p_threshold)
                or strategy.tweet_filter != old_strategy.tweet_filter):
            core.db.Indicator \
                .delete() \
                .where(core.db.Indicator.strategy_id == strategy.id) \
                .execute()

        return strategy

    @jwt_required()
    def delete(self):
        args = argp.parse_args()

        if not args.id:
            raise api.errors.InvalidArgument

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            strategy = core.db.Strategy.get_by_id(args.id)
            if strategy.user != user:
                raise api.errors.StrategyNotEditable
            strategy.delete_instance(recursive=True)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        return "", 204
