from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import pandas
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

        orders = pandas.DataFrame(position.get_orders().dicts())

        if orders.empty:
            return

        orders.price = orders.apply(
            lambda x: core.utils.qformat(x, "price"), axis=1)
        orders.amount = orders.apply(
            lambda x: core.utils.bformat(x, "amount"), axis=1)
        orders.cost = orders.apply(
            lambda x: core.utils.qformat(x, "cost"), axis=1)
        orders.filled = orders.apply(
            lambda x: core.utils.bformat(x, "filled"), axis=1)
        orders.fee = orders.apply(
            lambda x: core.utils.qformat(x, "fee"), axis=1)

        return orders.to_dict("records")
