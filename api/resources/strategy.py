from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import core

fields = {
    "id": fields.Integer,
    "subscribed": fields.Boolean,
    "market_id": fields.Integer,
    "active": fields.Boolean,
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


class Strategy(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        user_strats = [s for s in user.get_strategies()]
        strategies = [s for s in core.db.get_active_strategies()]

        for st in strategies:
            st.subscribed = False

        for st, u_st in zip(strategies, user_strats):
            if st == u_st:
                st.subscribed = True

        return strategies
