from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import core


balance_fields = {
    "ticker": fields.String,
    "free": fields.Float,
    "used": fields.Float,
    "total": fields.Float,
    "free_value": fields.Float,
    "used_value": fields.Float,
    "total_value": fields.Float,
}

fields = {
    "free_value": fields.Float,
    "used_value": fields.Float,
    "total_value": fields.Float,
    "positions_reserved": fields.Float,
    "positions_value": fields.Float,
    "balances": fields.List(fields.Nested(balance_fields)),
}


class Inventory(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        core.inventory.sync_balances(user)
        inventory = core.inventory.get_inventory(user)

        return inventory
