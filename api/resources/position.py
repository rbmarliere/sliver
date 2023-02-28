from decimal import Decimal as D

import pandas
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import api
import core


fields = {
    "id": fields.Integer,
    "market": fields.String,
    "strategy_id": fields.Integer,
    "status": fields.String,
    "target_cost": fields.Float,
    "entry_cost": fields.Float,
    "entry_amount": fields.Float,
    "entry_price": fields.Float,
    "exit_price": fields.Float,
    "exit_amount": fields.Float,
    "exit_cost": fields.Float,
    "fee": fields.Float,
    "pnl": fields.Float,
    "roi": fields.Float,
    "stopped": fields.Boolean,
    "entry_time": fields.DateTime(dt_format="iso8601"),
    "exit_time": fields.DateTime(dt_format="iso8601"),
}


def get_positions_df(query):
    positions = pandas.DataFrame(query.dicts())

    if positions.empty:
        return positions

    positions["market"] = positions.base_ticker + "/" + positions.quote_ticker

    base_precision = D("10") ** (D("-1") * positions.base_precision)
    quote_precision = D("10") ** (D("-1") * positions.quote_precision)

    positions.target_cost = positions.target_cost * quote_precision
    positions.target_cost = positions.apply(
        lambda x: core.utils.quantize(x, "target_cost", "price_precision"),
        axis=1)

    positions.entry_cost = positions.entry_cost * quote_precision
    positions.entry_cost = positions.apply(
        lambda x: core.utils.quantize(x, "entry_cost", "price_precision"),
        axis=1)

    positions.entry_amount = positions.entry_amount * base_precision
    positions.entry_amount = positions.apply(
        lambda x: core.utils.quantize(x, "entry_amount", "amount_precision"),
        axis=1)

    positions.entry_price = positions.entry_price * quote_precision
    positions.entry_price = positions.apply(
        lambda x: core.utils.quantize(x, "entry_price", "price_precision"),
        axis=1)

    positions.exit_price = positions.exit_price * quote_precision
    positions.exit_price = positions.apply(
        lambda x: core.utils.quantize(x, "exit_price", "price_precision"),
        axis=1)

    positions.exit_amount = positions.exit_amount * base_precision
    positions.exit_amount = positions.apply(
        lambda x: core.utils.quantize(x, "exit_amount", "amount_precision"),
        axis=1)

    positions.exit_cost = positions.exit_cost * quote_precision
    positions.exit_cost = positions.apply(
        lambda x: core.utils.quantize(x, "exit_cost", "price_precision"),
        axis=1)

    positions.fee = positions.fee * quote_precision
    positions.fee = positions.apply(
        lambda x: core.utils.quantize(x, "fee", "price_precision"),
        axis=1)

    positions.pnl = positions.pnl * quote_precision
    positions.pnl = positions.apply(
        lambda x: core.utils.quantize(x, "pnl", "price_precision"),
        axis=1)

    positions.roi = positions.roi.apply(lambda x: f"{x:.4f}")

    return positions


class Position(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, position_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)
        try:
            pos_q = user.get_positions() \
                .where(core.db.Position.id == position_id)
            pos = pos_q.get()
            return get_positions_df(pos_q).to_dict(orient="records")[0]
        except core.db.Position.DoesNotExist:
            raise api.errors.PositionDoesNotExist


class Positions(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)
        pos_q = user.get_positions()

        return get_positions_df(pos_q).to_dict("records")


class PositionsByStrategy(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, strategy_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)
        pos_q = user.get_positions() \
            .where(core.db.Strategy.id == strategy_id) \
            .where(core.db.Position.status == "closed") \
            .order_by(core.db.Position.id)

        return get_positions_df(pos_q).to_dict("records")
