from decimal import Decimal as D

import pandas
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

from sliver.api.exceptions import PositionDoesNotExist, StrategyDoesNotExist
from sliver.position import Position as PositionModel
from sliver.price import Price
from sliver.strategy import BaseStrategy as Strategy
from sliver.user import User
from sliver.utils import quantize

pos_fields = {
    "id": fields.Integer,
    "market": fields.String,
    "strategy_id": fields.Integer,
    "status": fields.String,
    "side": fields.String,
    "target_amount": fields.Float,
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

by_strategy_fields = {
    **pos_fields,
    "max_equity": fields.Float,
    "min_equity": fields.Float,
    "drawdown": fields.Float,
}


def get_positions_df(query):
    positions = pandas.DataFrame(query.dicts())

    if positions.empty:
        return positions

    positions["market"] = positions.base_ticker + "/" + positions.quote_ticker

    base_precision = D("10") ** (D("-1") * positions.base_precision)
    quote_precision = D("10") ** (D("-1") * positions.quote_precision)
    pnl_precision = D("10") ** (D("-1") * positions.pnl_precision)

    positions.target_amount = positions.target_amount * quote_precision
    positions.target_amount = positions.apply(
        lambda x: quantize(x, "target_amount", "amount_precision"), axis=1
    )

    positions.target_cost = positions.target_cost * quote_precision
    positions.target_cost = positions.apply(
        lambda x: quantize(x, "target_cost", "price_precision"), axis=1
    )

    positions.entry_cost = positions.entry_cost * quote_precision
    positions.entry_cost = positions.apply(
        lambda x: quantize(x, "entry_cost", "price_precision"), axis=1
    )

    positions.entry_amount = positions.entry_amount * base_precision
    positions.entry_amount = positions.apply(
        lambda x: quantize(x, "entry_amount", "amount_precision"), axis=1
    )

    positions.entry_price = positions.entry_price * quote_precision
    positions.entry_price = positions.apply(
        lambda x: quantize(x, "entry_price", "price_precision"), axis=1
    )

    positions.exit_price = positions.exit_price * quote_precision
    positions.exit_price = positions.apply(
        lambda x: quantize(x, "exit_price", "price_precision"), axis=1
    )

    positions.exit_amount = positions.exit_amount * base_precision
    positions.exit_amount = positions.apply(
        lambda x: quantize(x, "exit_amount", "amount_precision"), axis=1
    )

    positions.exit_cost = positions.exit_cost * quote_precision
    positions.exit_cost = positions.apply(
        lambda x: quantize(x, "exit_cost", "price_precision"), axis=1
    )

    positions.fee = positions.fee * quote_precision
    positions.fee = positions.apply(
        lambda x: quantize(x, "fee", "price_precision"), axis=1
    )

    positions.pnl = positions.pnl * pnl_precision
    positions.pnl = positions.apply(
        lambda x: quantize(
            x, "pnl", "price_precision" if x.side == "long" else "amount_precision"
        ),
        axis=1,
    )

    positions.roi = positions.roi.apply(lambda x: f"{x:.4f}")

    return positions


class Position(Resource):
    @marshal_with(pos_fields)
    @jwt_required()
    def get(self, position_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        pos_q = PositionModel.get_user_positions(user).where(
            PositionModel.id == position_id
        )
        pos = pos_q.get_or_none()

        if pos is None:
            raise PositionDoesNotExist

        return get_positions_df(pos_q).to_dict(orient="records")[0]


class Positions(Resource):
    @marshal_with(pos_fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)
        pos_q = PositionModel.get_user_positions(user)

        return get_positions_df(pos_q).to_dict("records")


class PositionsByStrategy(Resource):
    @marshal_with(by_strategy_fields)
    @jwt_required()
    def get(self, strategy_id):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            strategy = Strategy.get_by_id(strategy_id)
        except Strategy.DoesNotExist:
            raise StrategyDoesNotExist

        pos_q = (
            PositionModel.get_user_positions(user)
            .where(Strategy.id == strategy_id)
            .where(PositionModel.status == "closed")
            .order_by(PositionModel.id)
        )

        pos_df = get_positions_df(pos_q)

        if pos_df.empty:
            return pos_df.to_dict("records")

        pos_df["max_equity"] = pos_df.entry_cost
        pos_df["min_equity"] = pos_df.entry_cost
        pos_df["drawdown"] = 0

        for i, row in pos_df.iterrows():
            max_drawdown = 0
            max_equity = row.max_equity
            min_equity = row.min_equity

            prices = (
                Price.get_by_strategy(strategy)
                .where(Price.time >= row.entry_time)
                .where(Price.time <= row.exit_time)
            )

            for p in prices:
                curr_equity = p.close * row.entry_amount
                curr_drawdown = (curr_equity - max_equity) / max_equity * 100

                if curr_drawdown < max_drawdown:
                    max_drawdown = curr_drawdown

                if curr_equity > max_equity:
                    max_equity = curr_equity
                    min_equity = curr_equity

                if curr_equity < min_equity:
                    min_equity = curr_equity

            quote_precision = D("10") ** (D("-1") * row.quote_precision)
            price_precision = D("10") ** (D("-1") * row.price_precision)

            max_equity = max_equity * quote_precision
            max_equity = max_equity.quantize(price_precision)

            min_equity = min_equity * quote_precision
            min_equity = min_equity.quantize(price_precision)

            pos_df.loc[i, "drawdown"] = max_drawdown
            pos_df.loc[i, "max_equity"] = max_equity
            pos_df.loc[i, "min_equity"] = min_equity

        return pos_df.to_dict("records")
