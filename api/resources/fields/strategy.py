from flask_restful import fields, reqparse

import strategies


base_fields = {
    "id": fields.Integer,
    "symbol": fields.String,
    "exchange": fields.String,
    # "creator_id": fields.Integer,
    "description": fields.String,
    "type": fields.Integer,
    "active": fields.Boolean,
    # "deleted": fields.Boolean,
    "signal": fields.String,
    "market_id": fields.Integer,
    "timeframe": fields.String,
    # "next_refresh": fields.DateTime(dt_format="iso8601"),
    "orders_interval": fields.Integer,
    "num_orders": fields.Integer,
    "min_buckets": fields.Integer,
    "bucket_interval": fields.Integer,
    "spread": fields.Float,
    "stop_gain": fields.Float,
    "stop_loss": fields.Float,
    "lm_ratio": fields.Float,
    "subscribed": fields.Boolean,
}
price_fields = {
    "time": fields.List(fields.String),
    "open": fields.List(fields.Float),
    "high": fields.List(fields.Float),
    "low": fields.List(fields.Float),
    "close": fields.List(fields.Float),
    "volume": fields.List(fields.Float),
    "buys": fields.List(fields.Float),
    "sells": fields.List(fields.Float),
}

hypnox_indicators = {
    **price_fields,
    "i_score": fields.List(fields.Float),
    "p_score": fields.List(fields.Float),
}
hypnox_fields = {
    **base_fields,
    "i_threshold": fields.Float,
    "p_threshold": fields.Float,
    "tweet_filter": fields.String,
    "model_i": fields.String,
    "model_p": fields.String,
}

dd3_indicators = {
    **price_fields,
    "ma1": fields.List(fields.Float),
    "ma2": fields.List(fields.Float),
    "ma3": fields.List(fields.Float),
}
dd3_fields = {
    **base_fields,
    "ma1_period": fields.Integer,
    "ma2_period": fields.Integer,
    "ma3_period": fields.Integer,
}


def get_fields(type=None, all=True):
    if type == strategies.Types.MANUAL.value:
        pass

    elif type == strategies.Types.RANDOM.value:
        pass

    elif type == strategies.Types.HYPNOX.value:
        return hypnox_fields if all else hypnox_indicators

    elif type == strategies.Types.DD3.value:
        return dd3_fields if all else dd3_indicators

    return base_fields if all else price_fields


base_parser = reqparse.RequestParser()
base_parser.add_argument("id", type=int)
# base_parser.add_argument("symbol", type=str)
# base_parser.add_argument("exchange", type=str)
# base_parser.add_argument("signal", type=str)
# base_parser.add_argument("creator_id", type=int)
base_parser.add_argument("description", type=str)
base_parser.add_argument("type", type=int)
base_parser.add_argument("active", type=bool)
# base_parser.add_argument("deleted", type=bool)
base_parser.add_argument("market_id", type=int)
base_parser.add_argument("timeframe", type=str)
# base_parser.add_argument("next_refresh", type=inputs.datetime_from_iso8601)
base_parser.add_argument("orders_interval", type=int)
base_parser.add_argument("num_orders", type=int)
base_parser.add_argument("min_buckets", type=int)
base_parser.add_argument("bucket_interval", type=int)
base_parser.add_argument("spread", type=float)
base_parser.add_argument("stop_gain", type=float)
base_parser.add_argument("stop_loss", type=float)
base_parser.add_argument("lm_ratio", type=float)

base_parser.add_argument("subscribe", type=bool)
base_parser.add_argument("subscribed", type=bool)


def get_parser(type=None):
    if type == strategies.Types.MANUAL.value:
        base_parser.add_argument("signal", type=str)

    elif type == strategies.Types.RANDOM.value:
        pass

    elif type == strategies.Types.HYPNOX.value:
        base_parser.add_argument("i_threshold", type=float)
        base_parser.add_argument("p_threshold", type=float)
        base_parser.add_argument("tweet_filter", type=str)
        base_parser.add_argument("lm_ratio", type=float)
        base_parser.add_argument("model_i", type=str)
        base_parser.add_argument("model_p", type=str)

    return base_parser
