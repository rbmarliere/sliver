import decimal

import pandas
import peewee
import tensorflow_decision_forests as tfdf

import sliver.database as db
import sliver.models
from sliver.indicator import Indicator
from sliver.indicators.atr import ATR
from sliver.indicators.bb import BB
from sliver.indicators.hypnox import HYPNOX
from sliver.indicators.macd import MACD
from sliver.indicators.moon import MOON
from sliver.indicators.renko import RENKO
from sliver.print import print
from sliver.strategies.hypnox import HypnoxScore, HypnoxTweet, replay
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import quantize


class WindrunnerIndicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    z_score = peewee.DecimalField(null=True)
    mean = peewee.DecimalField(null=True)
    variance = peewee.DecimalField(null=True)
    n_samples = peewee.IntegerField(null=True)
    bolu = peewee.BigIntegerField(null=True)
    bold = peewee.BigIntegerField(null=True)
    macd = peewee.BigIntegerField(null=True)
    macd_signal = peewee.BigIntegerField(null=True)
    atr = peewee.BigIntegerField(null=True)
    moon_phase = peewee.IntegerField(null=True)
    operation = peewee.DecimalField(null=True)


class WindrunnerStrategy(IStrategy):
    windrunner_model = peewee.TextField(null=True)
    windrunner_upper_threshold = peewee.DecimalField(null=True)
    windrunner_lower_threshold = peewee.DecimalField(null=True)
    hypnox_model = peewee.TextField(null=True)
    hypnox_threshold = peewee.DecimalField(null=True)
    hypnox_filter = peewee.TextField(null=True)
    bb_num_std = peewee.IntegerField(null=True)
    bb_ma_period = peewee.IntegerField(null=True)
    bb_use_ema = peewee.BooleanField(null=True)
    macd_fast_period = peewee.IntegerField(null=True)
    macd_slow_period = peewee.IntegerField(null=True)
    macd_signal_period = peewee.IntegerField(null=True)
    macd_use_ema = peewee.BooleanField(null=True)
    atr_period = peewee.IntegerField(null=True)
    atr_ma_mode = peewee.TextField(null=True)
    renko_step = peewee.DecimalField(null=True)
    renko_use_atr = peewee.BooleanField(null=True)

    @staticmethod
    def get_indicator_class():
        return WindrunnerIndicator

    @staticmethod
    def setup():
        db.connection.create_tables([WindrunnerStrategy, WindrunnerIndicator])

    def get_indicators_df(self, **kwargs):
        df = super().get_indicators_df(**kwargs)

        if df.empty:
            return df

        df.bolu = df.bolu.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.bold = df.bold.apply(lambda x: decimal.Decimal(x) if x else 0)
        df.bolu = df.bolu * df.quote_precision
        df.bold = df.bold * df.quote_precision
        df.bolu = df.apply(lambda x: quantize(x, "bolu", "price_precision"), axis=1)
        df.bold = df.apply(lambda x: quantize(x, "bold", "price_precision"), axis=1)

        return df

    def refresh_indicators(self, indicators):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        if not self.hypnox_model or not self.windrunner_model:
            return

        filter = (
            self.hypnox_filter.encode("unicode_escape") if self.hypnox_filter else b""
        )

        base_q = (
            HypnoxTweet.get_tweets_by_model(self.hypnox_model)
            .where(HypnoxTweet.text.iregexp(filter))
            .where(HypnoxTweet.time > indicators.iloc[0].time)
        )

        replay_q = base_q.where(HypnoxScore.model.is_null())
        if replay_q.count() == 0:
            print(f"{self.hypnox_model}: no tweets to replay")
        else:
            model = sliver.models.load(self.hypnox_model)
            replay(replay_q, model)

        all_indicators = pandas.DataFrame(self.get_indicators().dicts())
        if len(all_indicators) == len(indicators):
            n_samples = 0
            mean = 0
            variance = 0
        else:
            n_samples = all_indicators.iloc[-1]["n_samples"]
            mean = all_indicators.iloc[-1]["mean"]
            variance = all_indicators.iloc[-1]["variance"]

        tweets = pandas.DataFrame(base_q.dicts())

        indicators = HYPNOX(
            indicators, tweets, self.timeframe, n_samples, mean, variance
        )
        indicators = BB(
            indicators,
            self.bb_ma_period,
            self.bb_num_std,
            self.bb_use_ema,
        )
        indicators = MACD(
            indicators,
            self.macd_fast_period,
            self.macd_slow_period,
            self.macd_signal_period,
        )
        indicators = ATR(indicators, self.atr_period, self.atr_ma_mode)
        indicators = MOON(indicators)
        bricks = RENKO(indicators, self.renko_step, self.renko_use_atr)

        model = sliver.models.load(self.windrunner_model)

        df = indicators.drop(columns=["open", "high", "low", "close"])
        bricks = bricks.merge(df, on="time")
        bricks = bricks.reset_index(drop=True)
        bricks = bricks[
            [
                "time",
                "open",
                "close",
                "z_score",
                "bolu",
                "bold",
                "macd",
                "macd_signal",
                "moon_phase",
            ]
        ]

        bricks["direction"] = -1
        bricks.loc[(bricks.close - bricks.open > 0), "direction"] = 1

        bricks.bolu = bricks.bolu / bricks.open
        bricks.bold = bricks.bold / bricks.open
        bricks.macd = bricks.macd / bricks.open
        bricks.macd_signal = bricks.macd_signal / bricks.open

        bricks_ds = tfdf.keras.pd_dataframe_to_tf_dataset(
            bricks.drop(columns=["time", "open", "close"])
        )
        bricks["operation"] = model.predict(bricks_ds)

        indicators = indicators.drop("operation", axis=1)
        indicators = indicators.merge(
            bricks[["time", "operation"]], on="time", how="outer"
        ).ffill()

        buy_rule = indicators.operation > float(self.windrunner_upper_threshold)
        sell_rule = indicators.operation < float(self.windrunner_lower_threshold)
        indicators["signal"] = NEUTRAL
        indicators.loc[buy_rule, "signal"] = BUY
        indicators.loc[sell_rule, "signal"] = SELL

        indicators = indicators.drop_duplicates(subset="id", keep="last")
        indicators = indicators.replace({float("nan"): 0})

        return indicators
