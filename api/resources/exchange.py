from flask_jwt_extended import jwt_required
from flask_restful import Resource, fields, marshal_with

import core

asset_fields = {
    "id": fields.Integer,
    "ticker": fields.String,
    "precision": fields.Integer
}

market_fields = {
    "base": fields.String,
    "quote": fields.String,
    "amount_precision": fields.Integer,
    "price_precision": fields.Integer,
    "amount_min": fields.String,
    "cost_min": fields.String,
    "price_min": fields.String
}

fields = {
    "name": fields.String,
    "rate_limit": fields.Integer,
    "rounding_mode": fields.String,
    "precision_mode": fields.String,
    "padding_mode": fields.String,
    "assets": fields.List(fields.Nested(asset_fields)),
    "markets": fields.List(fields.Nested(market_fields))
}


class Exchange(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        exchanges = []
        for ex in core.db.Exchange.select():
            asset_q = core.db.ExchangeAsset.select(core.db.Asset, core.db.ExchangeAsset).join(core.db.Asset).where(core.db.ExchangeAsset.exchange == ex)
            ex.assets = [a for a in asset_q.dicts()]

            markets_q = core.db.Market.select().join(core.db.ExchangeAsset, on=core.db.Market.base).where(core.db.Market.base.exchange == ex)
            ex.markets = [m for m in markets_q.dicts()]

            exchanges.append(ex)

        return exchanges

