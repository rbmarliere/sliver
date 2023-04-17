import decimal

import pandas
import peewee

import sliver.database as db
from sliver.indicator import Indicator
from sliver.indicators.rsi import RSI
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import quantize


class ElNinoIndicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    ma = peewee.BigIntegerField()
    rsi = peewee.DecimalField()


class ElNinoStrategy(IStrategy):
    elnino_ma_period = peewee.IntegerField(default=9)
    elnino_use_ema = peewee.BooleanField(default=False)
    elnino_buy_ma_offset = peewee.DecimalField(default=0)
    elnino_buy_rsi_min_threshold = peewee.DecimalField(default=30)
    elnino_buy_rsi_max_threshold = peewee.DecimalField(default=70)
    elnino_sell_ma_offset = peewee.DecimalField(default=0)
    elnino_sell_rsi_min_threshold = peewee.DecimalField(default=30)
    elnino_rsi_period = peewee.IntegerField(default=14)
    elnino_rsi_scalar = peewee.IntegerField(default=100)

    @staticmethod
    def get_indicator_class():
        return ElNinoIndicator

    @staticmethod
    def setup():
        db.connection.create_tables([ElNinoStrategy, ElNinoIndicator])

    def get_indicators_df(self):
        df = super().get_indicators_df()

        if df.empty:
            return df

        df.ma = df.ma.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma = df.ma * df.quote_precision
        df.ma = df.apply(lambda x: quantize(x, "ma", "price_precision"), axis=1)

        return df

    def refresh_indicators(self, indicators):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        # compute over whole set because of averages
        Indicator.delete().where(Indicator.strategy == self).execute()
        indicators = pandas.DataFrame(self.get_indicators().dicts())
        indicators.strategy = self.id
        indicators.price = indicators.id

        if self.elnino_use_ema:
            indicators.ma = indicators.close.ewm(self.elnino_ma_period).mean()
        else:
            indicators.ma = indicators.close.rolling(self.elnino_ma_period).mean()

        indicators.ma.fillna(method="bfill", inplace=True)

        indicators["buy_ma"] = indicators.ma * (
            1 + (float(self.elnino_buy_ma_offset) / 100)
        )
        indicators["sell_ma"] = indicators.ma * (
            1 + (float(self.elnino_sell_ma_offset) / 100)
        )

        indicators["rsi"] = RSI(
            indicators.close,
            period=self.elnino_rsi_period,
            scalar=self.elnino_rsi_scalar,
        )

        indicators.rsi.fillna(method="bfill", inplace=True)

        buy_rule = (
            (indicators.close >= indicators.ma)
            & (indicators.close <= indicators.buy_ma)
            & (indicators.rsi >= self.elnino_buy_rsi_min_threshold)
            & (indicators.rsi <= self.elnino_buy_rsi_max_threshold)
        )
        sell_rule = (
            (indicators.close >= indicators.ma)
            & (indicators.close >= indicators.sell_ma)
            & (indicators.rsi >= self.elnino_sell_rsi_min_threshold)
        )

        indicators["signal"] = NEUTRAL
        indicators.loc[buy_rule, "signal"] = BUY
        indicators.loc[sell_rule, "signal"] = SELL

        Indicator.insert_many(
            indicators[["strategy", "price", "signal"]].to_dict("records")
        ).execute()

        first = indicators[["strategy", "price", "signal"]].iloc[0]
        first_id = Indicator.get(**first.to_dict()).id
        indicators.indicator = range(first_id, first_id + len(indicators))

        ElNinoIndicator.insert_many(
            indicators[["indicator", "ma", "rsi"]].to_dict("records")
        ).execute()
