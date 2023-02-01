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
    "signal": fields.Float,
    "market_id": fields.Integer,
    "timeframe": fields.String,
    # "next_refresh": fields.DateTime(dt_format="iso8601"),
    "orders_interval": fields.Integer,
    "num_orders": fields.Integer,
    "min_buckets": fields.Integer,
    "bucket_interval": fields.Integer,
    "spread": fields.Float,
    "stop_gain": fields.Float,
    "trailing_gain": fields.Boolean,
    "stop_loss": fields.Float,
    "trailing_loss": fields.Boolean,
    "lm_ratio": fields.Float,
    "subscribed": fields.Boolean,
}
price_fields = {
    "time": fields.List(fields.String),
    "open": fields.List(fields.Float),
    # "high": fields.List(fields.Float),
    # "low": fields.List(fields.Float),
    "close": fields.List(fields.Float),
    # "volume": fields.List(fields.Float),
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

mixer_indicators = {
    **price_fields,
    "weighted_signal": fields.List(fields.Float),
}
mixer_fields = {
    **base_fields,
    "buy_threshold": fields.Float,
    "sell_threshold": fields.Float,
    "strategies": fields.List(fields.Integer),
    "weights": fields.List(fields.Float),
}

bb_indicators = {
    **price_fields,
    "ma": fields.List(fields.Float),
    "bolu": fields.List(fields.Float),
    "bold": fields.List(fields.Float),
}
bb_fields = {
    **base_fields,
    "use_ema": fields.Boolean,
    "ma_period": fields.Integer,
    "num_std": fields.Integer,
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

    elif type == strategies.Types.MIXER.value:
        return mixer_fields if all else mixer_indicators

    elif type == strategies.Types.BB.value:
        return bb_fields if all else bb_indicators

    return base_fields if all else price_fields


def get_subscription_parser():
    parser = reqparse.RequestParser()
    parser.add_argument("subscribe", type=bool, required=False)
    parser.add_argument("subscribed", type=bool, required=False)
    return parser


def get_activation_parser():
    parser = reqparse.RequestParser()
    parser.add_argument("activate", type=bool, required=False)
    parser.add_argument("active", type=bool, required=False)
    return parser


def get_base_parser(type=None):
    base_parser = reqparse.RequestParser()
    # ("id", type=int, required=False)
    # ("symbol", type=str, required=True)
    # ("exchange", type=str, required=True)
    # ("signal", type=str, required=True)
    # ("creator_id", type=int, required=True)
    base_parser.add_argument("description", type=str, required=True)
    base_parser.add_argument("type", type=int, required=True)
    # ("deleted", type=bool, required=True)
    base_parser.add_argument("market_id", type=int, required=True)
    base_parser.add_argument("timeframe", type=str, required=True)
    # ("next_refresh", type=inputs.datetime_from_iso8601, required=True)
    base_parser.add_argument("orders_interval", type=int, required=True)
    base_parser.add_argument("num_orders", type=int, required=True)
    base_parser.add_argument("min_buckets", type=int, required=True)
    base_parser.add_argument("bucket_interval", type=int, required=True)
    base_parser.add_argument("spread", type=float, required=True)
    base_parser.add_argument("stop_gain", type=float, required=True)
    base_parser.add_argument("trailing_gain", type=bool, required=True)
    base_parser.add_argument("stop_loss", type=float, required=True)
    base_parser.add_argument("trailing_loss", type=bool, required=True)
    base_parser.add_argument("lm_ratio", type=float, required=True)

    if type == strategies.Types.MANUAL.value:
        base_parser.add_argument("signal", type=float)

    elif type == strategies.Types.RANDOM.value:
        pass

    elif type == strategies.Types.HYPNOX.value:
        base_parser.add_argument("i_threshold", type=float, required=True)
        base_parser.add_argument("p_threshold", type=float, required=True)
        base_parser.add_argument("tweet_filter", type=str, required=True)
        base_parser.add_argument("model_i", type=str, required=True)
        base_parser.add_argument("model_p", type=str, required=True)

    elif type == strategies.Types.DD3.value:
        base_parser.add_argument("ma1_period", type=int, required=True)
        base_parser.add_argument("ma2_period", type=int, required=True)
        base_parser.add_argument("ma3_period", type=int, required=True)

    elif type == strategies.Types.MIXER.value:
        base_parser.add_argument("buy_threshold", type=float, required=True)
        base_parser.add_argument("sell_threshold", type=float, required=True)
        base_parser.add_argument("strategies",
                                 type=list,
                                 required=True,
                                 location="json")
        base_parser.add_argument("weights",
                                 type=list,
                                 required=True,
                                 location="json")

    elif type == strategies.Types.BB.value:
        base_parser.add_argument("use_ema", type=bool, required=True)
        base_parser.add_argument("ma_period", type=int, required=True)
        base_parser.add_argument("num_std", type=int, required=True)

    return base_parser
