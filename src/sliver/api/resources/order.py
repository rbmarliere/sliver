from decimal import Decimal as D

import pandas
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

from sliver.api.exceptions import OrderDoesNotExist, PositionDoesNotExist
from sliver.order import Order as OrderModel
from sliver.position import Position
from sliver.utils import quantize

fields = {
    "id": fields.Integer,
    "exchange_order_id": fields.String,
    "market": fields.String,
    "time": fields.DateTime(dt_format="iso8601"),
    "status": fields.String,
    "type": fields.String,
    "side": fields.String,
    "price": fields.String,
    "amount": fields.String,
    "cost": fields.String,
    "filled": fields.String,
    "fee": fields.String,
}


def get_orders_df(query):
    orders = pandas.DataFrame(query.dicts())

    if orders.empty:
        return orders

    orders["market"] = orders.base_ticker + "/" + orders.quote_ticker

    base_precision = D("10") ** (D("-1") * orders.base_precision)
    quote_precision = D("10") ** (D("-1") * orders.quote_precision)

    orders.price = orders.price * quote_precision
    orders.price = orders.apply(
        lambda x: quantize(x, "price", "price_precision"), axis=1
    )

    orders.amount = orders.amount * base_precision
    orders.amount = orders.apply(
        lambda x: quantize(x, "amount", "amount_precision"), axis=1
    )

    orders.cost = orders.cost * quote_precision
    orders.cost = orders.apply(lambda x: quantize(x, "cost", "price_precision"), axis=1)

    orders.filled = orders.filled * base_precision
    orders.filled = orders.apply(
        lambda x: quantize(x, "filled", "amount_precision"), axis=1
    )

    orders.fee = orders.fee * quote_precision
    orders.fee = orders.apply(lambda x: quantize(x, "fee", "price_precision"), axis=1)

    return orders


class Order(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, order_id):
        uid = int(get_jwt_identity())
        try:
            order = OrderModel.get_by_id(order_id)
            position = order.position
            if position.user_strategy.user.id != uid:
                raise OrderDoesNotExist
        except OrderModel.DoesNotExist:
            raise OrderDoesNotExist

        query = position.get_orders_full().where(OrderModel.id == order_id)

        return get_orders_df(query).to_dict("records")[0]


class Orders(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, position_id):
        uid = int(get_jwt_identity())
        try:
            position = Position.get_by_id(position_id)
            if position.user_strategy.user.id != uid:
                raise PositionDoesNotExist
        except Position.DoesNotExist:
            raise PositionDoesNotExist

        query = position.get_orders_full()

        return get_orders_df(query).to_dict("records")
