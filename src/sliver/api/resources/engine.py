import datetime

from flask_jwt_extended import jwt_required
from flask_restful import Resource, fields, marshal_with, reqparse

from sliver.api.exceptions import EngineDoesNotExist, EngineInUse, InvalidArgument
from sliver.position import Position
from sliver.strategy import BaseStrategy as Strategy
from sliver.trade_engine import TradeEngine

fields = {
    "id": fields.Integer,
    "description": fields.String,
    "refresh_interval": fields.Integer,
    "num_orders": fields.Integer,
    "bucket_interval": fields.Integer,
    "min_buckets": fields.Integer,
    "spread": fields.Float,
    "stop_cooldown": fields.Integer,
    "stop_gain": fields.Float,
    "trailing_gain": fields.Boolean,
    "stop_loss": fields.Float,
    "trailing_loss": fields.Boolean,
    "lm_ratio": fields.Float,
}

argp = reqparse.RequestParser()
argp.add_argument("description", type=str, required=True)
argp.add_argument("refresh_interval", type=int, required=True)
argp.add_argument("num_orders", type=int, required=True)
argp.add_argument("bucket_interval", type=int, required=True)
argp.add_argument("min_buckets", type=int, required=True)
argp.add_argument("spread", type=float, required=True)
argp.add_argument("stop_cooldown", type=int, required=True)
argp.add_argument("stop_gain", type=float, required=True)
argp.add_argument("trailing_gain", type=bool, required=True)
argp.add_argument("stop_loss", type=float, required=True)
argp.add_argument("trailing_loss", type=bool, required=True)
argp.add_argument("lm_ratio", type=float, required=True)


class Engines(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        q = TradeEngine.select().where(~TradeEngine.deleted).order_by(TradeEngine.id)

        return [e for e in q]

    @marshal_with(fields)
    @jwt_required()
    def post(self):
        args = argp.parse_args()

        if not args["description"]:
            raise InvalidArgument("Missing description")
        if args["stop_loss"]:
            args["stop_loss"] = abs(args.stop_loss)
        if args["stop_gain"]:
            args["stop_gain"] = abs(args.stop_gain)

        return TradeEngine.create(**args)


class Engine(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, engine_id):
        try:
            engine = TradeEngine.get_by_id(engine_id)
            if engine.deleted:
                raise EngineDoesNotExist
        except TradeEngine.DoesNotExist:
            raise EngineDoesNotExist

        return engine

    @marshal_with(fields)
    @jwt_required()
    def put(self, engine_id):
        try:
            engine = TradeEngine.get_by_id(engine_id)
            if engine.deleted:
                raise EngineDoesNotExist
        except TradeEngine.DoesNotExist:
            raise EngineDoesNotExist

        args = argp.parse_args()

        if not args["description"]:
            raise InvalidArgument("Missing description")
        if args["stop_loss"]:
            args["stop_loss"] = abs(args.stop_loss)
        if args["stop_gain"]:
            args["stop_gain"] = abs(args.stop_gain)

        for k, v in args.items():
            setattr(engine, k, v)

        engine.save()

        for p in Position.get_open().where(
            (Strategy.buy_engine_id == engine_id)
            | (Strategy.sell_engine_id == engine_id)
            | (Strategy.stop_engine_id == engine_id)
        ):
            p.next_refresh == datetime.datetime.utcnow()
            p.save()

        return engine

    @marshal_with(fields)
    @jwt_required()
    def delete(self, engine_id):
        try:
            engine = TradeEngine.get_by_id(engine_id)
            if engine.deleted:
                raise EngineDoesNotExist
        except TradeEngine.DoesNotExist:
            raise EngineDoesNotExist

        if engine.basestrategy_set.where(~Strategy.deleted).count() > 0:
            raise EngineInUse

        engine.deleted = True
        engine.save()

        return "", 204
