import pandas
import peewee
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, inputs, marshal_with, reqparse

import api
import core

price_fields = {
    "time": fields.List(fields.String),
    "open": fields.List(fields.Float),
    "high": fields.List(fields.Float),
    "low": fields.List(fields.Float),
    "close": fields.List(fields.Float),
    "volume": fields.List(fields.Float),
    "i_score": fields.List(fields.Float),
    "p_score": fields.List(fields.Float),
    "buys": fields.List(fields.Float),
    "sells": fields.List(fields.Float),
}

fields = {
    "symbol": fields.String,
    "exchange": fields.String,
    "market_id": fields.Integer,
    "id": fields.Integer,
    "subscribed": fields.Boolean,
    "active": fields.Boolean,
    "description": fields.String,
    "mode": fields.String,
    "timeframe": fields.String,
    "signal": fields.String,
    "refresh_interval": fields.Integer,
    "next_refresh": fields.DateTime(dt_format="iso8601"),
    "num_orders": fields.Integer,
    "bucket_interval": fields.Integer,
    "spread": fields.Float,
    "min_roi": fields.Float,
    "stop_loss": fields.Float,
    "i_threshold": fields.Float,
    "p_threshold": fields.Float,
    "tweet_filter": fields.String,
    "lm_ratio": fields.Float,
    "model_i": fields.String,
    "model_p": fields.String,
    "prices": fields.Nested(price_fields)
}

argp = reqparse.RequestParser()
argp.add_argument("market_id", type=int)
argp.add_argument("id", type=int)
argp.add_argument("subscribed", type=bool)
argp.add_argument("active", type=bool)
argp.add_argument("description", type=str)
argp.add_argument("mode", type=str)
argp.add_argument("timeframe", type=str)
argp.add_argument("signal", type=str)
argp.add_argument("refresh_interval", type=int)
argp.add_argument("next_refresh", type=inputs.datetime_from_iso8601)
argp.add_argument("num_orders", type=int)
argp.add_argument("bucket_interval", type=int)
argp.add_argument("spread", type=float)
argp.add_argument("min_roi", type=float)
argp.add_argument("stop_loss", type=float)
argp.add_argument("i_threshold", type=float)
argp.add_argument("p_threshold", type=float)
argp.add_argument("tweet_filter", type=str)
argp.add_argument("lm_ratio", type=float)
argp.add_argument("model_i", type=str)
argp.add_argument("model_p", type=str)


class Strategies(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        strategies = [s for s in
                      core.db.Strategy.select()
                      .where(core.db.Strategy.deleted == False)
                      .order_by(core.db.Strategy.id.desc())]

        for st in strategies:
            st.subscribed = user.is_subscribed(st)
            st.symbol = st.market.get_symbol()
            st.exchange = st.market.quote.exchange.name

        return strategies

    @marshal_with(fields)
    @jwt_required()
    def post(self):
        args = argp.parse_args()

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        if args.id and args.id > 0:
            return self.subscribe(args, user)
        else:
            return self.create(args, user)

    def subscribe(self, args, user):
        try:
            strategy = core.db.Strategy.get_by_id(args.id)
            if strategy.deleted:
                raise api.errors.StrategyDoesNotExist
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        user_strat_exists = False
        for u_st in user.userstrategy_set:
            if u_st.strategy == strategy:
                user_strat_exists = True
                u_st.active = args.subscribed
                u_st.save()

        if not user_strat_exists:
            core.db.UserStrategy(user=user,
                                 strategy=strategy,
                                 active=args.subscribed).save()

        strategy.subscribed = args.subscribed
        strategy.symbol = strategy.market.get_symbol()
        strategy.exchange = strategy.market.quote.exchange.name

        return strategy

    def create(self, args, user):
        strategy = core.db.Strategy(**args)
        strategy.id = None
        strategy.active = True
        strategy.user = user
        strategy.stop_loss = abs(strategy.stop_loss)
        strategy.min_roi = abs(strategy.min_roi)

        try:
            strategy.save()
        except (peewee.IntegrityError, core.db.Market.DoesNotExist):
            raise api.errors.InvalidArgument

        strategy.subscribed = False
        strategy.symbol = strategy.market.get_symbol()
        strategy.exchange = strategy.market.quote.exchange.name

        return strategy

    @marshal_with(fields)
    @jwt_required()
    def put(self):
        args = argp.parse_args()

        if not args.id:
            raise api.errors.InvalidArgument

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            old_strategy = core.db.Strategy.get_by_id(args.id)
            if old_strategy.deleted:
                raise api.errors.StrategyDoesNotExist
            market = old_strategy.market
            if old_strategy.user != user:
                raise api.errors.StrategyNotEditable
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        strategy = core.db.Strategy(**args)
        strategy.stop_loss = abs(strategy.stop_loss)
        strategy.min_roi = abs(strategy.min_roi)
        strategy.market = market
        strategy.save()

        strategy.subscribed = user.is_subscribed(strategy)
        strategy.symbol = strategy.market.get_symbol()
        strategy.exchange = strategy.market.quote.exchange.name

        if (strategy.i_threshold != float(old_strategy.i_threshold)
                or strategy.p_threshold != float(old_strategy.p_threshold)
                or strategy.tweet_filter != old_strategy.tweet_filter
                or strategy.model_i != old_strategy.model_i
                or strategy.model_p != old_strategy.model_p
                or strategy.mode != "auto"):
            core.db.Indicator \
                .delete() \
                .where(core.db.Indicator.strategy_id == strategy.id) \
                .execute()

        return strategy


class Strategy(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self, strategy_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
            if strategy.deleted:
                raise api.errors.StrategyDoesNotExist
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        if strategy.get_prices().count() == 0:
            core.exchange.download_prices(strategy)

        strategy.refresh_signal()

        strategy.symbol = strategy.market.get_symbol()
        strategy.exchange = strategy.market.quote.exchange.name
        strategy.subscribed = user.is_subscribed(strategy)

        ind = pandas.DataFrame(strategy.get_indicators().dicts())
        if not ind.empty:
            buys = []
            sells = []
            curr_pos = False
            for idx, row in ind.iterrows():
                if row.signal == "buy":
                    if not curr_pos:
                        buys.append(idx)
                        curr_pos = True
                elif row.signal == "sell":
                    if curr_pos:
                        sells.append(idx)
                        curr_pos = False
            ind.time = ind.time.dt.strftime("%Y-%m-%d %H:%M")
            ind.open = ind.open.apply(strategy.market.quote.format)
            ind.high = ind.high.apply(strategy.market.quote.format)
            ind.low = ind.low.apply(strategy.market.quote.format)
            ind.close = ind.close.apply(strategy.market.quote.format)
            ind.volume = ind.volume.apply(strategy.market.base.format)
            ind["buys"] = ind.open.where(ind.index.isin(buys))
            ind.buys = ind.buys.replace({float("nan"): None})
            ind["sells"] = ind.open.where(ind.index.isin(sells))
            ind.sells = ind.sells.replace({float("nan"): None})
            strategy.prices = ind.to_dict("list")

        return strategy

    @jwt_required()
    def delete(self, strategy_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            strategy = core.db.Strategy.get_by_id(strategy_id)
            if strategy.user != user:
                raise api.errors.StrategyNotEditable
            if strategy.get_active_users().count() > 0:
                raise api.errors.StrategyIsActive
            strategy.delete()
        except core.db.Strategy.DoesNotExist:
            raise api.errors.StrategyDoesNotExist

        return "", 204
