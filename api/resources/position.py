import pandas
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import core

fields = {
    "id": fields.Integer,
    "market": fields.String,
    "strategy_id": fields.Integer,
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

        positions = pandas.DataFrame(user.get_positions().dicts())

        if positions.empty:
            return

        positions["market"] = positions.apply(
            lambda x: core.utils.sformat(x), axis=1)
        positions.target_cost = positions.apply(
            lambda x: core.utils.qformat(x, "target_cost"), axis=1)
        positions.entry_cost = positions.apply(
            lambda x: core.utils.qformat(x, "entry_cost"), axis=1)
        positions.entry_amount = positions.apply(
            lambda x: core.utils.bformat(x, "entry_amount"), axis=1)
        positions.entry_price = positions.apply(
            lambda x: core.utils.qformat(x, "entry_price"), axis=1)
        positions.exit_price = positions.apply(
            lambda x: core.utils.qformat(x, "exit_price"), axis=1)
        positions.exit_amount = positions.apply(
            lambda x: core.utils.bformat(x, "exit_amount"), axis=1)
        positions.exit_cost = positions.apply(
            lambda x: core.utils.qformat(x, "exit_cost"), axis=1)
        positions.fee = positions.apply(
            lambda x: core.utils.qformat(x, "fee"), axis=1)
        positions.pnl = positions.apply(
            lambda x: core.utils.qformat(x, "pnl"), axis=1)

        return positions.to_dict("records")
