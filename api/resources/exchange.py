from flask_jwt_extended import jwt_required
from flask_restful import Resource, fields, marshal_with

import core

asset_fields = {
    "id": fields.Integer,
    "ticker": fields.String,
    "precision": fields.Integer
}

market_fields = {
    "symbol": fields.String,
    "id": fields.Integer,
    "base_id": fields.Integer,
    "quote_id": fields.Integer,
    "amount_precision": fields.Integer,
    "price_precision": fields.Integer,
    "amount_min": fields.Integer,
    "cost_min": fields.Integer,
    "price_min": fields.Integer
}

fields = {
    "name": fields.String,
    "rate_limit": fields.Integer,
    "precision_mode": fields.Integer,
    "padding_mode": fields.Integer,
    "timeframes": fields.List(fields.String),
    "assets": fields.List(fields.Nested(asset_fields)),
    "markets": fields.List(fields.Nested(market_fields))
}


class Exchange(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        exchanges = []
        for ex in core.db.Exchange.select():
            asset_q = core.db.ExchangeAsset \
                .select(core.db.Asset, core.db.ExchangeAsset) \
                .join(core.db.Asset) \
                .where(core.db.ExchangeAsset.exchange == ex)

            ex.assets = [a for a in asset_q.dicts()]

            markets_q = core.db.Market \
                .select() \
                .join(core.db.ExchangeAsset, on=core.db.Market.base) \
                .where(core.db.Market.base.exchange == ex)

            ex.markets = []
            for m in markets_q:
                m.symbol = m.get_symbol()
                ex.markets.append(m)

            ex.timeframes = eval(ex.timeframes) if ex.timeframes else []

            exchanges.append(ex)

        return exchanges
