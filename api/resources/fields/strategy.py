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
    "subscribed": fields.Boolean,
    "buy_engine_id": fields.Integer,
    "sell_engine_id": fields.Integer,
    "stop_engine_id": fields.Integer,
}
indicators_fields = {
    "time": fields.List(fields.DateTime(dt_format="iso8601")),
    "open": fields.List(fields.Float),
    "high": fields.List(fields.Float),
    "low": fields.List(fields.Float),
    "close": fields.List(fields.Float),
    "volume": fields.List(fields.Float),
    "buys": fields.List(fields.Float),
    "sells": fields.List(fields.Float),
    "signal": fields.List(fields.Float),
}

hypnox_indicators = {
    **indicators_fields,
    "z_score": fields.List(fields.Float),
}
hypnox_fields = {
    **base_fields,
    "threshold": fields.Float,
    "filter": fields.String,
    "model": fields.String,
    "mode": fields.String,
    "operator": fields.String,
}

dd3_indicators = {
    **indicators_fields,
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
    **indicators_fields,
    "buy_w_signal": fields.List(fields.Float),
    "sell_w_signal": fields.List(fields.Float),
}
mixer_fields = {
    **base_fields,
    "buy_threshold": fields.Float,
    "sell_threshold": fields.Float,
    "strategies": fields.List(fields.Integer),
    "buy_weights": fields.List(fields.Float),
    "sell_weights": fields.List(fields.Float),
}

bb_indicators = {
    **indicators_fields,
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

ma_cross_indicators = {
    **indicators_fields,
    "fast": fields.List(fields.Float),
    "slow": fields.List(fields.Float),
}
ma_cross_fields = {
    **base_fields,
    "use_fast_ema": fields.Boolean,
    "fast_period": fields.Integer,
    "use_slow_ema": fields.Boolean,
    "slow_period": fields.Integer,
}

swapperbox_indicators = {
    **indicators_fields,
}
swapperbox_fields = {
    **base_fields,
    "url": fields.String,
    "telegram": fields.String,
}


def get_fields(type=None, all=True):
    if type == strategies.Types.MANUAL:
        pass

    elif type == strategies.Types.RANDOM:
        pass

    elif type == strategies.Types.HYPNOX:
        return hypnox_fields if all else hypnox_indicators

    elif type == strategies.Types.DD3:
        return dd3_fields if all else dd3_indicators

    elif type == strategies.Types.MIXER:
        return mixer_fields if all else mixer_indicators

    elif type == strategies.Types.BB:
        return bb_fields if all else bb_indicators

    elif type == strategies.Types.MA_CROSS:
        return ma_cross_fields if all else ma_cross_indicators

    elif type == strategies.Types.SWAPPERBOX:
        return swapperbox_fields if all else swapperbox_indicators

    return base_fields if all else indicators_fields


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
    base_parser.add_argument("buy_engine_id", type=int, required=True)
    base_parser.add_argument("sell_engine_id", type=int, required=True)
    base_parser.add_argument("stop_engine_id", type=int, required=True)

    if type == strategies.Types.MANUAL:
        base_parser.add_argument("signal", type=float)

    elif type == strategies.Types.RANDOM:
        pass

    elif type == strategies.Types.HYPNOX:
        base_parser.add_argument("threshold", type=float, required=True)
        base_parser.add_argument("filter", type=str, required=True)
        base_parser.add_argument("model", type=str, required=True)
        base_parser.add_argument("mode", type=str, required=True)
        base_parser.add_argument("operator", type=str, required=True)

    elif type == strategies.Types.DD3:
        base_parser.add_argument("ma1_period", type=int, required=True)
        base_parser.add_argument("ma2_period", type=int, required=True)
        base_parser.add_argument("ma3_period", type=int, required=True)

    elif type == strategies.Types.MIXER:
        base_parser.add_argument("buy_threshold", type=float, required=True)
        base_parser.add_argument("sell_threshold", type=float, required=True)
        base_parser.add_argument(
            "strategies", type=list, required=True, location="json"
        )
        base_parser.add_argument(
            "buy_weights", type=list, required=True, location="json"
        )
        base_parser.add_argument(
            "sell_weights", type=list, required=True, location="json"
        )

    elif type == strategies.Types.BB:
        base_parser.add_argument("use_ema", type=bool, required=True)
        base_parser.add_argument("ma_period", type=int, required=True)
        base_parser.add_argument("num_std", type=int, required=True)

    elif type == strategies.Types.MA_CROSS:
        base_parser.add_argument("use_fast_ema", type=bool, required=True)
        base_parser.add_argument("fast_period", type=int, required=True)
        base_parser.add_argument("use_slow_ema", type=bool, required=True)
        base_parser.add_argument("slow_period", type=int, required=True)

    elif type == strategies.Types.SWAPPERBOX:
        base_parser.add_argument("url", type=str, required=True)
        base_parser.add_argument("telegram", type=str, required=True)

    return base_parser
