from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import api.errors
import core

fields = {
    "time": fields.DateTime,
    "status": fields.String,
    "type": fields.String,
    "side": fields.String,
    "price": fields.String,
    "amount": fields.String,
    "cost": fields.String,
    "filled": fields.String,
    "fee": fields.String
}


class Order(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, position_id):
        uid = int(get_jwt_identity())
        try:
            position = core.db.Position.get_by_id(position_id)
        except core.db.Position.DoesNotExist:
            raise api.errors.PositionDoesNotExist

        if position.user_strategy.user.id != uid:
            raise api.errors.PositionDoesNotExist

        return [o for o in position.get_orders()]
