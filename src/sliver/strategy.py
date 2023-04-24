import datetime
from flask_restful import reqparse, fields

from abc import ABCMeta, abstractmethod
from decimal import Decimal as D

import pandas
import peewee

import sliver.database as db
from sliver.exchanges.factory import ExchangeFactory
from sliver.indicator import Indicator
from sliver.market import Market
from sliver.price import Price
from sliver.print import print
from sliver.strategies.signals import StrategySignals
from sliver.trade_engine import TradeEngine
from sliver.utils import (
    get_next_refresh,
    get_timeframe_in_seconds,
    quantize,
    parse_field_type,
)


class BaseStrategy(db.BaseModel):
    __metaclass__ = ABCMeta

    class Meta:
        table_name = "strategy"

    creator = peewee.DeferredForeignKey("User", null=True)
    description = peewee.TextField()
    type = peewee.IntegerField(default=0)
    active = peewee.BooleanField(default=False)
    deleted = peewee.BooleanField(default=False)
    market = peewee.ForeignKeyField(Market)
    timeframe = peewee.TextField(default="1d")
    next_refresh = peewee.DateTimeField(default=datetime.datetime.utcnow())
    buy_engine = peewee.ForeignKeyField(TradeEngine)
    sell_engine = peewee.ForeignKeyField(TradeEngine)
    stop_engine = peewee.ForeignKeyField(TradeEngine, null=True)
    side = peewee.TextField(default="long")

    @property
    def symbol(self):
        return self.market.get_symbol()

    @property
    def exchange(self):
        return self.market.base.exchange.name

    @classmethod
    def get_existing(cls):
        return cls.select().where(~cls.deleted).order_by(cls.id.desc())

    @classmethod
    def get_active(cls):
        return cls.get_existing().where(cls.active)

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

    def get_signal(self):
        try:
            signal = (
                self.indicator_set.join(Price).order_by(Price.time.desc()).get().signal
            )
            return StrategySignals(signal)
        except Indicator.DoesNotExist:
            return StrategySignals.NEUTRAL

    def get_indicators(self, model=None):
        select_fields = [Price, Indicator.id.alias("indicator_id"), Indicator]

        query = Price.get_by_strategy(self).join(
            Indicator,
            peewee.JOIN.LEFT_OUTER,
            on=((Indicator.price_id == Price.id) & (Indicator.strategy == self)),
        )

        if model:
            select_fields.append(model)
            query = query.join(model, peewee.JOIN.LEFT_OUTER)

        return query.select(*select_fields)

    def get_indicators_df(self, query=None):
        BUY = StrategySignals.BUY
        SELL = StrategySignals.SELL

        if query is None:
            query = self.get_indicators()

        df = pandas.DataFrame(query.dicts())

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
        self.active = True
        self.next_refresh = datetime.datetime.utcnow()
        self.save()

    def disable(self):
        print(
            f"disabled strategy {self.id} - {self.description} "
            f"for {self.symbol} @ {self.market.quote.exchange.name}",
            notice=True,
        )
        for dep in self.mixedstrategies_set:
            dep.mixer.disable()
        self.active = False
        self.save()

    def delete(self):
        self.deleted = True
        self.active = False
        self.save()

    def postpone(self, interval_in_minutes=None):
        if interval_in_minutes is None:
            interval_in_minutes = get_timeframe_in_seconds(self.timeframe) / 60
        self.next_refresh = get_next_refresh(interval_in_minutes)
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
    def refresh_indicators(self, indicators):
        ...

    def get_indicators(self):
        return self.strategy.get_indicators(model=self.get_indicator_class())

    def get_indicators_df(self):
        return self.strategy.get_indicators_df(self.get_indicators())

    def refresh(self):
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

        ExchangeFactory.from_base(self.market.base.exchange).fetch_ohlcv(self)

        pending = self.get_pending_indicators()
        if not pending.empty:
            print("refreshing indicators")
            with db.connection.atomic():
                self.refresh_indicators(pending)

        print(f"signal is {self.get_signal()}")

        self.postpone()

    def get_pending_indicators(self):
        df = pandas.DataFrame(self.get_indicators().dicts())

        if df.empty:
            return df

        df["strategy"] = self.strategy.id
        df["price"] = df.id

        return df.loc[df.indicator_id.isnull()].copy()

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
