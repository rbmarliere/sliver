import datetime
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
from sliver.strategies.types import StrategyTypes
from sliver.trade_engine import TradeEngine
from sliver.user import User
from sliver.utils import get_next_refresh, get_timeframe_in_seconds, quantize


class BaseStrategy(db.BaseModel):
    __metaclass__ = ABCMeta

    class Meta:
        table_name = "strategy"

    creator = peewee.ForeignKeyField(User)
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

    @property
    def symbol(self):
        return self.market.get_symbol()

    @property
    def exchange(self):
        return self.market.base.exchange.name

    @property
    def signal(self):
        try:
            signal = (
                self.indicator_set.where(Indicator.signal != StrategySignals.NEUTRAL)
                .order_by(Indicator.price_id.desc())
                .get()
                .signal
            )
            return StrategySignals(signal)
        except Indicator.DoesNotExist:
            return StrategySignals.NEUTRAL

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
            .where(cls.active)
            .where(cls.next_refresh < datetime.datetime.utcnow())
            .order_by(cls.next_refresh)
            .order_by(cls.type == StrategyTypes.MIXER)
        )

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

        df.replace({float("nan"): None}, inplace=True)

        return df

    def enable(self):
        self.active = True
        self.next_refresh = datetime.datetime.utcnow()
        self.save()

    def disable(self):
        print("disabling strategy {s}...".format(s=self))
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
        print(
            "postponed strategy {i} next refresh at {n}".format(
                i=self.id, n=self.next_refresh
            )
        )
        self.save()


class IStrategy(db.BaseModel):
    __metaclass__ = ABCMeta
    strategy = peewee.ForeignKeyField(BaseStrategy, primary_key=True)

    @property
    def id(self):
        return self.strategy.id

    def __getattr__(self, attr):
        return getattr(self.strategy, attr)

    def refresh(self):
        print("===========================================")
        print("refreshing strategy {s}".format(s=self))
        print("market is {m} {i}".format(m=self.market.get_symbol(), i=self.market.id))
        print("timeframe is {T}".format(T=self.timeframe))
        print("exchange is {e}".format(e=self.market.base.exchange.name))
        print("type is {m}".format(m=StrategyTypes(self.type).name))
        print("buy engine is {e}".format(e=self.buy_engine_id))
        print("sell engine is {e}".format(e=self.sell_engine_id))
        print("stop engine is {e}".format(e=self.stop_engine_id))

        ExchangeFactory.from_base(self.market.base.exchange).fetch_ohlcv(self)

        self.refresh_indicators()

        print("signal is {s}".format(s=self.signal.name))

        self.postpone()

    @abstractmethod
    def refresh_indicators(self):
        ...
