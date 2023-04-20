from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

from sliver.user import User

balance_fields = {
    "ticker": fields.String,
    "total": fields.Float,
}

fields = {
    "balances": fields.List(fields.Nested(balance_fields)),
}


class Inventory(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        return user.get_inventory()
