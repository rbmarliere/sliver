import datetime
from abc import ABCMeta, abstractmethod
from decimal import Decimal as D

import pandas
import peewee
from flask_restful import fields, reqparse

import sliver.database as db
from sliver.exchanges.factory import ExchangeFactory
from sliver.indicator import Indicator
from sliver.market import Market
from sliver.price import Price
from sliver.print import print
from sliver.strategies.signals import StrategySignals
from sliver.strategies.status import StrategyStatus
from sliver.trade_engine import TradeEngine
from sliver.utils import (
    get_next_refresh,
    get_timeframe_in_seconds,
    parse_field_type,
    quantize,
)


class BaseStrategy(db.BaseModel):
    __metaclass__ = ABCMeta

    class Meta:
        table_name = "strategy"

    creator = peewee.DeferredForeignKey("User", null=True)
    description = peewee.TextField()
    type = peewee.IntegerField(default=0)
    market = peewee.ForeignKeyField(Market)
    timeframe = peewee.TextField(default="1d")
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    next_refresh_offset = peewee.IntegerField(default=0)
    buy_engine = peewee.ForeignKeyField(TradeEngine)
    sell_engine = peewee.ForeignKeyField(TradeEngine)
    stop_engine = peewee.ForeignKeyField(TradeEngine, null=True)
    side = peewee.TextField(default="long")
    status = peewee.IntegerField(default=StrategyStatus.INACTIVE)

    @property
    def symbol(self):
        return self.market.get_symbol()

    @property
    def exchange(self):
        return self.market.base.exchange.name

    @classmethod
    def get_existing(cls):
        return (
            cls.select()
            .where(cls.status != StrategyStatus.DELETED)
            .order_by(cls.id.desc())
        )

    @classmethod
    def get_active(cls):
        return cls.get_existing().where(cls.status << StrategyStatus.active())

    @classmethod
    def get_pending(cls):
        return (
            cls.get_active()
            .where(cls.next_refresh < datetime.datetime.utcnow())
            .order_by(cls.type == 4)  # MIXER
            .order_by(cls.next_refresh)
        )

    @staticmethod
    def get_parser():
        argp = reqparse.RequestParser()
        argp.add_argument("description", type=str, required=True)
        argp.add_argument("type", type=int, required=True)
        argp.add_argument("next_refresh_offset", type=int, required=True)
        argp.add_argument("side", type=str, required=True)
        argp.add_argument("market_id", type=int, required=True)
        argp.add_argument("timeframe", type=str, required=True)
        argp.add_argument("buy_engine_id", type=int, required=True)
        argp.add_argument("sell_engine_id", type=int, required=True)
        argp.add_argument("stop_engine_id", type=int, required=True)

        return argp

    @staticmethod
    def get_fields():
        return {
            "id": fields.Integer,
            "symbol": fields.String,
            "exchange": fields.String,
            "description": fields.String,
            "type": fields.Integer,
            "next_refresh_offset": fields.Integer,
            "side": fields.String,
            "active": fields.Boolean,
            "signal": fields.Integer,
            "market_id": fields.Integer,
            "timeframe": fields.String,
            "subscribed": fields.Boolean,
            "buy_engine_id": fields.Integer,
            "sell_engine_id": fields.Integer,
            "stop_engine_id": fields.Integer,
        }

    @staticmethod
    def get_indicator_fields():
        return {
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

    @property
    def active(self):
        return self.is_active()

    def is_deleted(self):
        return self.status == StrategyStatus.DELETED

    def is_active(self):
        return self.status in StrategyStatus.active()

    def is_refreshing(self):
        return self.status in StrategyStatus.refreshing()

    def get_signal(self):
        try:
            signal = (
                self.indicator_set.join(Price).order_by(Price.time.desc()).get().signal
            )
            return StrategySignals(signal)
        except Indicator.DoesNotExist:
            return StrategySignals.NEUTRAL

    def get_indicators(self, model=None, join_type=None):
        if join_type is None:
            join_type = peewee.JOIN.LEFT_OUTER

        select_fields = [Price, Indicator.id.alias("indicator_id"), Indicator]

        query = Price.get_by_strategy(self).join(
            Indicator,
            join_type,
            on=((Indicator.price_id == Price.id) & (Indicator.strategy == self)),
        )

        if model:
            select_fields.append(model)
            query = query.join(model, join_type)

        return query.select(*select_fields)

    def get_indicators_df(self, query=None, join_type=None, since=None, until=None):
        BUY = StrategySignals.BUY
        SELL = StrategySignals.SELL

        if query is None:
            query = self.get_indicators(join_type=join_type)

        df = pandas.DataFrame(query.dicts())

        if df.empty:
            return df

        if since is not None:
            since = datetime.datetime.utcfromtimestamp(since)
            df = df.loc[df.time >= since].copy()

        if until is not None:
            until = datetime.datetime.utcfromtimestamp(until)
            df = df.loc[df.time <= until].copy()

        if df.empty:
            return df

        def p(p):
            return D("10") ** (D("-1") * p)

        self.amount_precision = D(self.market.amount_precision)
        self.base_precision = p(self.market.base.precision)
        self.price_precision = D(self.market.price_precision)
        self.quote_precision = p(self.market.quote.precision)

        df["amount_precision"] = self.amount_precision
        df["base_precision"] = self.base_precision
        df["price_precision"] = self.price_precision
        df["quote_precision"] = self.quote_precision

        df.open = df.open * df.quote_precision
        df.high = df.high * df.quote_precision
        df.low = df.low * df.quote_precision
        df.close = df.close * df.quote_precision
        df.volume = df.volume * df.base_precision

        df = df.set_index("time")
        sig = df.loc[df.signal != 0]

        # remove consecutive duplicated signals
        b = sig.loc[sig.signal.shift() != sig.signal].loc[sig.signal == BUY].index
        s = sig.loc[sig.signal.shift() != sig.signal].loc[sig.signal == SELL].index

        df["buys"] = D(0)
        df["sells"] = D(0)

        df.loc[b, "buys"] = df.loc[b, "close"].fillna(D(0)) * D("0.995")
        df.loc[s, "sells"] = df.loc[s, "close"].fillna(D(0)) * D("1.005")

        df = df.reset_index()

        df.buys = df.apply(lambda x: quantize(x, "buys", "price_precision"), axis=1)
        df.buys.replace({0: None}, inplace=True)

        df.sells = df.apply(lambda x: quantize(x, "sells", "price_precision"), axis=1)
        df.sells.replace({0: None}, inplace=True)

        df.open = df.apply(lambda x: quantize(x, "open", "price_precision"), axis=1)
        df.high = df.apply(lambda x: quantize(x, "high", "price_precision"), axis=1)
        df.low = df.apply(lambda x: quantize(x, "low", "price_precision"), axis=1)
        df.close = df.apply(lambda x: quantize(x, "close", "price_precision"), axis=1)
        df.volume = df.apply(
            lambda x: quantize(x, "volume", "amount_precision"), axis=1
        )

        return df

    def enable(self):
        self.status = StrategyStatus.IDLE
        self.next_refresh = datetime.datetime.utcnow()
        self.save()

    def disable(self):
        msg = (
            f"disabled strategy {self.id} - {self.description} "
            f"for {self.symbol} @ {self.market.quote.exchange.name}"
        )

        print(msg, notice=True)
        for dep in self.mixedstrategies_set:
            dep.mixer.disable()
        for u_st in self.userstrategy_set:
            if u_st.active:
                u_st.user.send_message(msg)

        self.status = StrategyStatus.INACTIVE
        self.save()

    def delete(self):
        self.status = StrategyStatus.DELETED
        self.save()

    def postpone(self, interval_in_minutes=None):
        if interval_in_minutes is None:
            interval_in_minutes = get_timeframe_in_seconds(self.timeframe) / 60

        offset = datetime.timedelta(minutes=self.next_refresh_offset)
        self.next_refresh = get_next_refresh(interval_in_minutes) + offset

        print(f"postponed strategy {self} next refresh at {self.next_refresh}")
        self.save()


class IStrategy(db.BaseModel):
    __metaclass__ = ABCMeta
    strategy = peewee.ForeignKeyField(BaseStrategy, primary_key=True)

    @property
    def id(self):
        return self.strategy.id

    def __getattr__(self, attr):
        return getattr(self.strategy, attr)

    @staticmethod
    def get_indicator_class():
        return None

    @staticmethod
    @abstractmethod
    def setup():
        ...

    @abstractmethod
    def refresh_indicators(self, indicators, pending, reset=False):
        ...

    def get_indicators(self, **kwargs):
        return self.strategy.get_indicators(model=self.get_indicator_class(), **kwargs)

    def get_indicators_df(self, **kwargs):
        return self.strategy.get_indicators_df(self.get_indicators(), **kwargs)

    def refresh(self):
        reset = self.strategy.status == StrategyStatus.RESETTING

        self.strategy.status = StrategyStatus.REFRESHING
        self.strategy.save()

        print("===========================================")
        print(f"refreshing strategy {self}")
        print(f"market is {self.symbol} [{self.market}]")
        print(f"side is {self.side}")
        print(f"timeframe is {self.timeframe}")
        print(f"exchange is {self.market.base.exchange.name}")
        print(f"type is {self.type}")
        print(f"buy engine is {self.buy_engine_id}")
        print(f"sell engine is {self.sell_engine_id}")
        print(f"stop engine is {self.stop_engine_id}")

        print("refreshing indicators")
        indicators = pandas.DataFrame(self.get_indicators().dicts())
        indicators.strategy = self.strategy.id
        indicators.price = indicators.id
        pending = indicators.loc[indicators.indicator_id.isnull()].copy()

        with db.connection.atomic():
            indicators = self.refresh_indicators(indicators, pending, reset=reset)
            if indicators is not None:
                self.update_indicators(indicators)

        signal = self.get_signal()
        print(f"signal is {signal}")

        self.postpone()

        self.strategy.status = StrategyStatus.IDLE
        self.strategy.save()

        for u_st in self.strategy.userstrategy_set:
            u_st.refresh(signal)

    def get_parser(self):
        argp = BaseStrategy.get_parser()

        for field in self.__data__:
            if field == "strategy":
                continue
            argp.add_argument(
                f"{field}", type=type(self.__data__[field]), required=True
            )

        return argp

    def get_fields(self):
        all_fields = BaseStrategy.get_fields()

        for field in self.__data__:
            if field == "strategy":
                continue
            field_type = type(self.__data__[field])
            all_fields[field] = parse_field_type(field_type)

        return all_fields

    def get_indicator_fields(self):
        all_fields = BaseStrategy.get_indicator_fields()

        if self.get_indicator_class() is None:
            return all_fields

        try:
            i = self.get_indicator_class().get()
        except self.get_indicator_class().DoesNotExist:
            return all_fields

        for field in i.__data__:
            if field == "indicator":
                continue
            field_type = type(i.__data__[field])
            all_fields[field] = fields.List(parse_field_type(field_type))

        return all_fields

    def update_indicators(self, indicators):
        Indicator.insert_many(
            indicators[["strategy", "price", "signal"]].to_dict("records")
        ).on_conflict(
            conflict_target=[Indicator.strategy, Indicator.price],
            preserve=[Indicator.signal],
        ).execute()

        model = self.get_indicator_class()
        if model is None:
            return

        updated = pandas.DataFrame(self.get_indicators().dicts())
        indicators.indicator = updated.indicator_id

        model_field_names = [f for f in model._meta.fields]
        model_fields = [
            getattr(model, f) for f in model_field_names if f != "indicator"
        ]

        model.insert_many(indicators[model_field_names].to_dict("records")).on_conflict(
            conflict_target=[model.indicator],
            preserve=model_fields,
        ).execute()
