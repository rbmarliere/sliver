from decimal import Decimal as D

import pandas
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import api.errors
import core


fields = {
    "exchange_order_id": fields.String,
    "time": fields.DateTime(dt_format="iso8601"),
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

        orders = pandas.DataFrame(position.get_orders_full().dicts())

        if orders.empty:
            return orders.to_dict("records")

        base_precision = D("10") ** (D("-1") * orders.base_precision)
        quote_precision = D("10") ** (D("-1") * orders.quote_precision)

        orders.price = orders.price * quote_precision
        orders.price = orders.apply(
            lambda x: core.utils.quantize(x, "price", "price_precision"),
            axis=1)

        orders.amount = orders.amount * base_precision
        orders.amount = orders.apply(
            lambda x: core.utils.quantize(x, "amount", "amount_precision"),
            axis=1)

        orders.cost = orders.cost * quote_precision
        orders.cost = orders.apply(
            lambda x: core.utils.quantize(x, "cost", "price_precision"),
            axis=1)

        orders.filled = orders.filled * base_precision
        orders.filled = orders.apply(
            lambda x: core.utils.quantize(x, "filled", "amount_precision"),
            axis=1)

        orders.fee = orders.fee * quote_precision
        orders.fee = orders.apply(
            lambda x: core.utils.quantize(x, "fee", "price_precision"),
            axis=1)

        return orders.to_dict("records")
