import pandas
import peewee

import core
import models
from ..base import BaseStrategy
from strategies.hypnox.replay import replay


print = core.watchdog.Watchdog().print


class HypnoxUser(core.db.BaseModel):
    twitter_user_id = peewee.TextField(null=True)
    username = peewee.TextField()


class HypnoxTweet(core.db.BaseModel):
    time = peewee.DateTimeField()
    text = peewee.TextField()

    def get_tweets_by_model(model: str):
        return (
            HypnoxTweet.select(HypnoxTweet, HypnoxScore)
            .join(
                HypnoxScore,
                peewee.JOIN.LEFT_OUTER,
                on=(
                    (HypnoxScore.tweet_id == HypnoxTweet.id)
                    & (HypnoxScore.model == model)
                ),
            )
            .order_by(HypnoxTweet.time)
        )


class HypnoxScore(core.db.BaseModel):
    tweet = peewee.ForeignKeyField(HypnoxTweet, on_delete="CASCADE")
    model = peewee.TextField()
    score = peewee.DecimalField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (tweet_id, model)")]


class HypnoxIndicator(core.db.BaseModel):
    indicator = peewee.ForeignKeyField(
        core.db.Indicator, primary_key=True, on_delete="CASCADE"
    )
    z_score = peewee.DecimalField()
    mean = peewee.DecimalField()
    variance = peewee.DecimalField()
    n_samples = peewee.IntegerField()


class HypnoxStrategy(BaseStrategy):
    threshold = peewee.DecimalField(default=0)
    filter = peewee.TextField(null=True)
    model = peewee.TextField(null=True)
    mode = peewee.TextField(default="buy")
    operator = peewee.TextField(default="gt")

    def get_indicators(self):
        return (
            super()
            .get_indicators()
            .select(*[*self.select_fields, HypnoxIndicator])
            .join(HypnoxIndicator, peewee.JOIN.LEFT_OUTER)
        )

    def get_indicators_df(self):
        return super().get_indicators_df(self.get_indicators())

    def refresh(self):
        # update tweet scores
        if self.model:
            query = HypnoxTweet.get_tweets_by_model(self.model).where(
                HypnoxScore.model.is_null()
            )

            count = query.count()
            if count == 0:
                print("{m}: no tweets to replay".format(m=self.model))
            else:
                model = models.load_model(self.model)
                replay(query, model)

        self.refresh_indicators()

    def refresh_indicators(self):
        BUY = core.strategies.Signal.BUY
        NEUTRAL = core.strategies.Signal.NEUTRAL
        SELL = core.strategies.Signal.SELL

        # grab indicators
        indicators_q = self.get_indicators()
        indicators = pandas.DataFrame(indicators_q.dicts())

        # filter relevant data
        self_regex = self.filter.encode("unicode_escape") if self.filter else b""
        f = HypnoxTweet.text.iregexp(self_regex)
        f = f & (HypnoxScore.model.is_null(False))
        existing = indicators.dropna()
        indicators = indicators[indicators.isnull().any(axis=1)]
        if indicators.empty:
            print("indicator data is up to date")
            return 0
        f = f & (HypnoxTweet.time > indicators.iloc[0].time)

        # grab scores
        tweets_q = HypnoxTweet.get_tweets_by_model(self.model).where(f)
        if tweets_q.count() == 0:
            print("no tweets found for given regex")
            return 0

        tweets = pandas.DataFrame(tweets_q.dicts())
        tweets = tweets.set_index("time")

        # grab last computed metrics
        if existing.empty:
            n_samples = 0
            mean = 0
            variance = 0
        else:
            n_samples = existing.iloc[-1]["n_samples"]
            mean = existing.iloc[-1]["mean"]
            variance = existing.iloc[-1]["variance"]

        # compute new metrics
        mean, variance = core.utils.get_mean_var(
            tweets.score, n_samples, mean, variance
        )

        # apply normalization
        tweets["z_score"] = (tweets.score - mean) / variance.sqrt()

        # resample tweets by strat timeframe freq median
        freq = core.utils.get_timeframe_freq(self.strategy.timeframe)
        tweets = tweets[["z_score"]].resample(freq).median().ffill()

        # join both dataframes
        indicators = indicators.set_index("time")
        indicators = indicators.drop("z_score", axis=1)
        indicators = pandas.concat([indicators, tweets], join="inner", axis=1)
        if indicators.empty:
            print("indicator data is up to date")
            return 0

        # fill out remaining columns
        indicators = indicators.drop("price", axis=1)
        indicators["strategy"] = self.strategy.id
        indicators["n_samples"] = n_samples + len(tweets)
        indicators["mean"] = mean
        indicators["variance"] = variance

        # compute signals
        indicators["signal"] = NEUTRAL

        signal = NEUTRAL
        if self.mode == "buy":
            signal = BUY
        elif self.mode == "sell":
            signal = SELL

        rule = indicators["z_score"] == self.threshold
        if self.operator == "gt":
            rule = indicators["z_score"] > self.threshold
        elif self.operator == "lt":
            rule = indicators["z_score"] < self.threshold

        indicators.loc[rule, "signal"] = signal

        indicators = indicators.reset_index()
        indicators = indicators.rename(
            columns={
                "id": "price_id",
                "strategy": "strategy_id",
            }
        )

        with core.db.connection.atomic():
            vanilla_indicators = indicators[
                [
                    "strategy_id",
                    "price_id",
                    "signal",
                ]
            ]
            core.db.Indicator.insert_many(
                vanilla_indicators.to_dict("records")
            ).execute()

            hypnox_indicators = indicators[
                ["z_score", "mean", "variance", "n_samples"]
            ].copy()

            first_id = core.db.Indicator.get(**vanilla_indicators.iloc[0].to_dict()).id
            hypnox_indicators.insert(
                0, "indicator_id", range(first_id, first_id + len(indicators))
            )
            HypnoxIndicator.insert_many(hypnox_indicators.to_dict("records")).execute()
