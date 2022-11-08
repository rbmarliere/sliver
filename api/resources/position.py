from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import core

fields = {
    "id": fields.Integer,
    "market_id": fields.Integer,
    "strategy_id": fields.Integer,
    "next_bucket": fields.DateTime,
    "bucket_max": fields.String,
    "bucket": fields.String,
    "status": fields.String,
    "target_cost": fields.String,
    "entry_cost": fields.String,
    "entry_amount": fields.String,
    "entry_price": fields.String,
    "exit_price": fields.String,
    "exit_amount": fields.String,
    "exit_cost": fields.String,
    "fee": fields.String,
    "pnl": fields.String,
}


class Position(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        return [p for p in user.get_positions()]
