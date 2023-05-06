import decimal

import peewee
from pandas_ta.momentum.rsi import rsi

import sliver.database as db
from sliver.indicator import Indicator
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import quantize

from pandas_ta.overlap.ma import ma


class LaNinaIndicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    rsi = peewee.DecimalField()
    root_ma = peewee.BigIntegerField()
    ma1 = peewee.BigIntegerField()
    ma2 = peewee.BigIntegerField()
    ma3 = peewee.BigIntegerField()
    trend = peewee.BigIntegerField()


class LaNinaStrategy(IStrategy):
    lanina_rsi_period = peewee.IntegerField(default=14)
    lanina_rsi_scalar = peewee.IntegerField(default=100)

    lanina_buy_rsi_min_threshold = peewee.DecimalField(default=30)
    lanina_buy_rsi_max_threshold = peewee.DecimalField(default=70)
    lanina_sell_rsi_min_threshold = peewee.DecimalField(default=30)

    lanina_root_ma_period = peewee.IntegerField(default=20)
    lanina_root_ma_mode = peewee.TextField(default="sma")
    lanina_ma1_period = peewee.IntegerField(default=3)
    lanina_ma1_mode = peewee.TextField(default="sma")
    lanina_ma2_period = peewee.IntegerField(default=8)
    lanina_ma2_mode = peewee.TextField(default="sma")
    lanina_ma3_period = peewee.IntegerField(default=20)
    lanina_ma3_mode = peewee.TextField(default="sma")

    lanina_stopbuy_ma_min_offset = peewee.DecimalField(default=0)
    lanina_buy_ma_min_offset = peewee.DecimalField(default=0)
    lanina_buy_ma_max_offset = peewee.DecimalField(default=0)
    lanina_sell_ma_min_offset = peewee.DecimalField(default=0)

    lanina_cross_active = peewee.BooleanField(default=False)
    lanina_cross_buyback_offset = peewee.IntegerField(default=0)
    lanina_cross_buy_min_closes_above = peewee.IntegerField(default=1)
    lanina_cross_sell_min_closes_below = peewee.IntegerField(default=1)
    lanina_cross_reversed_below = peewee.BooleanField(default=False)

    lanina_bull_cross_active = peewee.BooleanField(default=False)

    @staticmethod
    def get_indicator_class():
        return LaNinaIndicator

    @staticmethod
    def setup():
        db.connection.create_tables([LaNinaStrategy, LaNinaIndicator])

    def get_indicators_df(self, **kwargs):
        df = super().get_indicators_df(**kwargs)

        if df.empty:
            return df

        df.root_ma = df.root_ma.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.root_ma = df.root_ma * df.quote_precision
        df.root_ma = df.apply(
            lambda x: quantize(x, "root_ma", "price_precision"), axis=1
        )

        df.ma1 = df.ma1.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma1 = df.ma1 * df.quote_precision
        df.ma1 = df.apply(lambda x: quantize(x, "ma1", "price_precision"), axis=1)

        df.ma2 = df.ma2.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma2 = df.ma2 * df.quote_precision
        df.ma2 = df.apply(lambda x: quantize(x, "ma2", "price_precision"), axis=1)

        df.ma3 = df.ma3.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.ma3 = df.ma3 * df.quote_precision
        df.ma3 = df.apply(lambda x: quantize(x, "ma3", "price_precision"), axis=1)

        return df

    def refresh_indicators(self, indicators, pending, reset=False):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        indicators["rsi"] = rsi(
            indicators.close,
            length=self.lanina_rsi_period,
            scalar=self.lanina_rsi_scalar,
        )

        indicators["root_ma"] = ma(
            self.lanina_root_ma_mode,
            indicators.close,
            length=self.lanina_root_ma_period,
        )
        indicators["ma1"] = ma(
            self.lanina_ma1_mode, indicators.close, length=self.lanina_ma1_period
        )
        indicators["ma2"] = ma(
            self.lanina_ma2_mode, indicators.close, length=self.lanina_ma2_period
        )
        indicators["ma3"] = ma(
            self.lanina_ma3_mode, indicators.close, length=self.lanina_ma3_period
        )

        indicators.rsi.fillna(method="bfill", inplace=True)
        indicators.root_ma.fillna(method="bfill", inplace=True)
        indicators.ma1.fillna(method="bfill", inplace=True)
        indicators.ma2.fillna(method="bfill", inplace=True)
        indicators.ma3.fillna(method="bfill", inplace=True)

        indicators["buy_min_ma_stop"] = indicators.root_ma * (
            1 - (abs(float(self.lanina_stopbuy_ma_min_offset)) / 100)
        )
        indicators["buy_min_ma"] = indicators.root_ma * (
            1 - (abs(float(self.lanina_buy_ma_min_offset)) / 100)
        )
        indicators["buy_max_ma"] = indicators.root_ma * (
            1 + (abs(float(self.lanina_buy_ma_max_offset)) / 100)
        )
        indicators["sell_min_ma"] = indicators.root_ma * (
            1 + (abs(float(self.lanina_sell_ma_min_offset)) / 100)
        )

        buy_rule = (
            (indicators.close >= indicators.root_ma)
            & (indicators.close <= indicators.buy_max_ma)
            & (indicators.close >= indicators.buy_min_ma)
            & (indicators.rsi >= self.lanina_buy_rsi_min_threshold)
            & (indicators.rsi <= self.lanina_buy_rsi_max_threshold)
        )

        sell_rule = (
            (indicators.close >= indicators.root_ma)
            & (indicators.close >= indicators.sell_min_ma)
            & (indicators.rsi >= self.lanina_sell_rsi_min_threshold)
        )

        indicators["signal"] = NEUTRAL
        indicators["elnino"] = NEUTRAL
        indicators.loc[buy_rule, "elnino"] = BUY
        indicators.loc[sell_rule, "elnino"] = SELL

        bear_trend = (indicators.ma1 <= indicators.ma2) & (
            indicators.ma2 <= indicators.ma3
        )
        bull_trend = (indicators.ma1 >= indicators.ma2) & (
            indicators.ma2 >= indicators.ma3
        )
        indicators["trend"] = 0
        indicators.loc[bear_trend, "trend"] = -1
        indicators.loc[bull_trend, "trend"] = 1

        if self.lanina_cross_active:
            prev = indicators.shift(1)
            bear_cross = bear_trend & ((prev.trend == 1) | (prev.trend == 0))
            indicators.loc[(bear_cross) & (bear_trend), "sell_stop"] = SELL
            indicators.sell_stop = indicators.sell_stop.shift(
                abs(self.lanina_cross_sell_min_closes_below)
            )
            indicators.loc[
                (indicators.sell_stop.notnull()) | (indicators.elnino == SELL), "signal"
            ] = SELL

            if self.lanina_bull_cross_active:
                bull_cross = bull_trend & ((prev.trend == -1) | (prev.trend == 0))

                indicators.loc[(bull_cross) & (bull_trend), "buy_stop"] = BUY
                indicators.buy_stop = indicators.buy_stop.shift(
                    abs(self.lanina_cross_buy_min_closes_above)
                )

                indicators.loc[
                    (indicators.buy_stop.notnull())
                    & (
                        (indicators.close <= indicators.buy_min_ma_stop)
                        | (indicators.close <= indicators.buy_max_ma)
                    ),
                    "buy_asap",
                ] = BUY

                # the first buy signal is always a buy_asap, therefore we remove all
                # buy_stop that come after a sell_stop until a buy_asap signal
                indicators.loc[indicators.sell_stop == SELL, "buy_asap"] = SELL
                indicators.buy_asap.fillna(method="ffill", inplace=True)

                indicators.loc[
                    ((indicators.buy_asap == BUY) & (indicators.buy_stop == BUY))
                    | (
                        (indicators.buy_asap == BUY)
                        & (indicators.elnino == BUY)
                        & (bull_trend)
                    ),
                    "signal",
                ] = BUY

            else:
                indicators.loc[indicators.elnino == BUY, "signal"] = BUY
        else:
            indicators.loc[indicators.elnino == SELL, "signal"] = SELL

        indicators.signal.fillna(NEUTRAL, inplace=True)

        # buying at a bull cross is only allowed if the last sell signal was
        # from the bear cross, so we remove all buys that come after a normal
        # sell signal (that are put in the stop aux. column as '2')

        # bkp = indicators.loc[indicators.signal == SELL, "buy_stop"].copy()
        # indicators.loc[indicators.signal == SELL, "buy_stop"] = 2
        # stops = indicators.loc[
        #     indicators.buy_stop.notnull() & indicators.buy_stop != NEUTRAL
        # ]
        # prev_stops = stops.shift(1)
        # stops.loc[
        #     (prev_stops.buy_stop == 2) & (stops.buy_stop == BUY),
        #     "buy_stop",
        # ] = NEUTRAL
        # indicators.loc[indicators.signal == SELL, "buy_stop"] = bkp
        # indicators.loc[
        #     indicators.buy_stop.notnull(), "buy_stop"
        # ] = stops.buy_stop

        # also, any normal buy ('3') that happens after a bear cross and close
        # price is below root_ma is removed

        # indicators.loc[(indicators.signal == BUY), "stop"] = 3
        # indicators.loc[(indicators.buy_stop == BUY), "stop"] = BUY
        # indicators.loc[(indicators.sell_stop == SELL), "stop"] = SELL
        # group = indicators.stop.lt(3).cumsum()
        # indicators["stop_clean"] = indicators.groupby(group)["stop"].cummin()

        # add eligible buys to signal col.

        # indicators.loc[indicators.stop == 3, "signal"] = BUY
        # indicators.loc[
        #     (indicators.stop == 3)
        #     & (indicators.stop_clean == SELL)
        #     & (indicators.close <= indicators.root_ma),
        #     "signal",
        # ] = NEUTRAL
        # indicators.loc[indicators.stop == BUY, "signal"] = BUY

        # if self.lanina_cross_reversed_below:
        #     # TODO
        #     buy_rule = buy_rule & bull
        #     sell_rule = sell_rule & bear

        # Level 0: It trades exactly like it does right now, only above the MA, in an
        #   "uptrend/bullish trend"

        # Level 1: It trades like it does now, except that it has a stoploss when the
        #   3MAs cross "bearish", will buy at next buy signal whenever price goes above
        #   the main MA again

        # Level 2: It trades like it does now, and has a stoploss when the 3MAs cross
        #   "bearish" with an option to buy X% Lower. If it doesn't get to buy X% lower,
        #   it will just buy at the next buy signal and continue trading as per normal.
        #   If it does buy X% lower, then it just sells at the next sell signal

        # Level 3: It trades like it does now, and when the three MAs cross bearish,
        #   not only does it add a stoploss, but it changes strategy to work in reverse,
        #   so it follows the trend down, selling close to the MA and buying further
        #   away from it, like in the screenshot we talked about

        return indicators
