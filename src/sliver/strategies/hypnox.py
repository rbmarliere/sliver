import numpy
import pandas
import peewee

import sliver.database as db
import sliver.models
from sliver.indicator import Indicator
from sliver.indicators.hypnox import HYPNOX
from sliver.print import print
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import standardize


def predict(model, tweets, verbose=0):
    inputs = model.tokenizer(
        tweets,
        truncation=True,
        padding="max_length",
        max_length=model.max_length,
        return_tensors="tf",
    )

    prob = model.predict(
        {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]},
        batch_size=model.batch_size,
        verbose=verbose,
    )

    if model.type == "polarity":
        indexes = prob.argmax(axis=1)
        values = numpy.take_along_axis(
            prob, numpy.expand_dims(indexes, axis=1), axis=1
        ).squeeze(axis=1)
        labels = [-1 if x == 2 else x for x in indexes]

        scores = labels * values

    elif model.type == "intensity":
        scores = prob.flatten()

    return scores


def replay(query, model, verbose=0):
    print(f"{model.name}: replaying {query.count()} tweets")

    with db.connection.atomic():
        tweets = pandas.DataFrame(query.dicts())
        tweets.text = tweets.text.apply(standardize)
        tweets.text = tweets.text.str.slice(0, model.max_length)
        tweets = tweets.rename(columns={"id": "tweet_id"})
        tweets["model"] = model.name
        tweets["score"] = predict(model, tweets["text"].to_list(), verbose=verbose)

        scores = tweets[["tweet_id", "model", "score"]]

        try:
            HypnoxScore.insert_many(scores.to_dict("records")).execute()

        except Exception:
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

    def refresh_indicators(self, indicators):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        if self.model:
            filter = self.filter.encode("unicode_escape") if self.filter else b""

            base_q = (
                HypnoxTweet.get_tweets_by_model(self.model)
                .where(HypnoxTweet.text.iregexp(filter))
                .where(HypnoxTweet.time > indicators.iloc[0].time)
            )

            replay_q = base_q.where(HypnoxScore.model.is_null())
            if replay_q.count() == 0:
                print(f"{self.model}: no tweets to replay")
            else:
                model = sliver.models.load(self.model)
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
            indicators, tweets, self.strategy.timeframe, n_samples, mean, variance
        )

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

        Indicator.insert_many(
            indicators[["strategy", "price", "signal"]].to_dict("records")
        ).execute()

        first = indicators[["strategy", "price", "signal"]].iloc[0]
        first_id = Indicator.get(**first.to_dict()).id
        indicators.indicator = range(first_id, first_id + len(indicators))

        HypnoxIndicator.insert_many(
            indicators[
                ["indicator", "z_score", "mean", "variance", "n_samples"]
            ].to_dict("records")
        ).execute()
