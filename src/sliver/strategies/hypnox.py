import numpy
import pandas
import peewee

import sliver.database as db
import sliver.models
from sliver.indicator import Indicator
from sliver.print import print
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import get_mean_var, get_timeframe_freq, standardize


def predict(model, tweets, verbose=0):
    inputs = model.tokenizer(
        tweets,
        truncation=True,
        padding="max_length",
        max_length=model.config["max_length"],
        return_tensors="tf",
    )

    prob = model.predict(
        {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]},
        batch_size=model.config["batch_size"],
        verbose=verbose,
    )

    if model.config["class"] == "polarity":
        indexes = prob.argmax(axis=1)
        values = numpy.take_along_axis(
            prob, numpy.expand_dims(indexes, axis=1), axis=1
        ).squeeze(axis=1)
        labels = [-1 if x == 2 else x for x in indexes]

        scores = labels * values

    elif model.config["class"] == "intensity":
        scores = prob.flatten()

    return scores


def replay(query, model, verbose=0):
    print("{m}: replaying {c} tweets".format(c=query.count(), m=model.config["name"]))

    with db.connection.atomic():
        # page = 0
        # while True:
        # page_q = query.paginate(page, 1024)
        # page += 1
        # if page_q.count() == 0:
        #     break

        tweets = pandas.DataFrame(query.dicts())
        tweets.text = tweets.text.apply(standardize)
        tweets.text = tweets.text.str.slice(0, model.config["max_length"])
        tweets = tweets.rename(columns={"id": "tweet_id"})
        tweets["model"] = model.config["name"]
        tweets["score"] = predict(model, tweets["text"].to_list(), verbose=verbose)

        scores = tweets[["tweet_id", "model", "score"]]

        try:
            HypnoxScore.insert_many(scores.to_dict("records")).execute()

        except Exception:
            # drop to a python interpreter shell
            import code

            code.interact(local=locals())


class HypnoxUser(db.BaseModel):
    twitter_user_id = peewee.TextField(null=True)
    username = peewee.TextField()


class HypnoxTweet(db.BaseModel):
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


class HypnoxScore(db.BaseModel):
    tweet = peewee.ForeignKeyField(HypnoxTweet, on_delete="CASCADE")
    model = peewee.TextField()
    score = peewee.DecimalField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (tweet_id, model)")]


class HypnoxIndicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    z_score = peewee.DecimalField()
    mean = peewee.DecimalField()
    variance = peewee.DecimalField()
    n_samples = peewee.IntegerField()


class HypnoxStrategy(IStrategy):
    threshold = peewee.DecimalField(default=0)
    filter = peewee.TextField(null=True)
    model = peewee.TextField(null=True)
    mode = peewee.TextField(default="buy")
    operator = peewee.TextField(default="gt")

    def get_indicators(self):
        return self.strategy.get_indicators(model=HypnoxIndicator)

    def get_indicators_df(self):
        return self.strategy.get_indicators_df(self.get_indicators())

    def refresh_indicators(self):
        if self.model:
            query = HypnoxTweet.get_tweets_by_model(self.model).where(
                HypnoxScore.model.is_null()
            )

            count = query.count()
            if count == 0:
                print("{m}: no tweets to replay".format(m=self.model))
            else:
                model = sliver.models.load_model(self.model)
                replay(query, model)

        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

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
        mean, variance = get_mean_var(tweets.score, n_samples, mean, variance)

        # apply normalization
        tweets["z_score"] = (tweets.score - mean) / variance.sqrt()

        # resample tweets by strat timeframe freq median
        freq = get_timeframe_freq(self.strategy.timeframe)
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

        with db.connection.atomic():
            vanilla_indicators = indicators[
                [
                    "strategy_id",
                    "price_id",
                    "signal",
                ]
            ]
            Indicator.insert_many(vanilla_indicators.to_dict("records")).execute()

            hypnox_indicators = indicators[
                ["z_score", "mean", "variance", "n_samples"]
            ].copy()

            first_id = Indicator.get(**vanilla_indicators.iloc[0].to_dict()).id
            hypnox_indicators.insert(
                0, "indicator_id", range(first_id, first_id + len(indicators))
            )
            HypnoxIndicator.insert_many(hypnox_indicators.to_dict("records")).execute()
