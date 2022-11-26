import pandas
import peewee
from flask_jwt_extended import jwt_required
from flask_restful import Resource, fields, marshal_with

import api
import core

fields = {
    "time": fields.List(fields.String),
    "open": fields.List(fields.Float),
    "high": fields.List(fields.Float),
    "low": fields.List(fields.Float),
    "close": fields.List(fields.Float),
    "volume": fields.List(fields.Float),
    "signal": fields.List(fields.String),
    "i_score": fields.List(fields.Float),
    "p_score": fields.List(fields.Float),
    "buys": fields.List(fields.Float),
    "sells": fields.List(fields.Float),
}


class Price(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, strategy_id):
        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        q = strategy\
            .get_prices() \
            .join(core.db.Indicator, peewee.JOIN.LEFT_OUTER) \
            .select(core.db.Price, core.db.Indicator) \
            .order_by(core.db.Price.id)

        prices = pandas.DataFrame(q.dicts())

        if prices.empty:
            return

        prices.time = prices.time.dt.strftime("%Y-%m-%d %H:%M")
        prices.open = prices.open.apply(strategy.market.quote.format)
        prices.high = prices.high.apply(strategy.market.quote.format)
        prices.low = prices.low.apply(strategy.market.quote.format)
        prices.close = prices.close.apply(strategy.market.quote.format)
        prices.volume = prices.volume.apply(strategy.market.base.format)

        prices["buys"] = (
            (1 + .003) *
            prices.close
            .where(prices.signal == "buy"))
        prices.buys = prices.buys.replace({float("nan"): None})

        prices["sells"] = (
            (1 - .003) *
            prices.close
            .where(prices.signal == "sell"))
        prices.sells = prices.sells.replace({float("nan"): None})

        return prices.to_dict("list")
