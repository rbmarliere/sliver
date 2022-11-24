from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with, reqparse

import api
import core

fields = {
    "id": fields.Integer,
    "subscribed": fields.Boolean,
    "symbol": fields.String,
    "description": fields.String,
    "mode": fields.String,
    "timeframe": fields.String,
    "signal": fields.String,
    "refresh_interval": fields.Integer,
    "next_refresh": fields.DateTime,
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
argp.add_argument("strategy_id", type=int, required=True)
argp.add_argument("subscribed", type=bool, required=True)


class Strategy(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        user_strats = [s.strategy for s in user.userstrategy_set.where(
            core.db.UserStrategy.active)]
        strategies = [s for s in core.db.get_active_strategies()]

        for st in strategies:
            st.subscribed = False
            if st in user_strats:
                st.subscribed = True

            st.symbol = st.market.get_symbol()

        return strategies

    @marshal_with(fields)
    @jwt_required()
    def post(self):
        args = argp.parse_args()

        try:
            strategy = core.db.Strategy.get_by_id(args.strategy_id)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

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

        return strategy
