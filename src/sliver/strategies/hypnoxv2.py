import nltk
import pandas
import peewee
from tqdm import tqdm

import sliver.database as db
from sliver.exceptions import DisablingError
from sliver.indicator import Indicator
from sliver.strategies.hypnox import HypnoxTweet
from sliver.strategies.signals import StrategySignals
from sliver.strategy import IStrategy
from sliver.utils import clean_text, get_timeframe_freq, standardize


def aggregate_tweets(tweets, pos_bigrams, neg_bigrams, unigrams):
    words = clean_text("".join(str(tweets.tolist())))

    bigrams = pandas.Series(nltk.ngrams(words, 2)).value_counts()

    pos = bigrams[bigrams.index.map(str).isin(pos_bigrams.index)]
    neg = bigrams[bigrams.index.map(str).isin(neg_bigrams.index)]

    for idx, item in pos.items():
        if idx[0] in unigrams or idx[1] in unigrams:
            pos[idx] *= 2

    for idx, item in neg.items():
        if idx[0] in unigrams or idx[1] in unigrams:
            neg[idx] *= 2

    return pos.sum() - neg.sum()


class Hypnoxv2Gram(db.BaseModel):
    rank = peewee.IntegerField(default=1)
    gram = peewee.TextField()
    label = peewee.IntegerField(default=0)

    @classmethod
    def get_by_rank(cls, rank):
        grams = pandas.DataFrame(cls.select().where(cls.rank == rank).dicts())

        if grams.empty:
            return grams

        grams = grams.set_index("gram")[["label"]]

        return grams


class Hypnoxv2Indicator(db.BaseModel):
    indicator = peewee.ForeignKeyField(Indicator, primary_key=True, on_delete="CASCADE")
    score = peewee.DecimalField()


class Hypnoxv2Strategy(IStrategy):
    hypnoxv2_tweet_filter = peewee.TextField(null=True)
    hypnoxv2_upper_threshold = peewee.DecimalField(default=0)
    hypnoxv2_lower_threshold = peewee.DecimalField(default=0)

    @staticmethod
    def get_indicator_class():
        return Hypnoxv2Indicator

    @staticmethod
    def setup():
        db.connection.create_tables([Hypnoxv2Strategy, Hypnoxv2Indicator, Hypnoxv2Gram])

    def refresh_indicators(self, indicators, pending, reset=False):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        if reset:
            pending = indicators

        if pending.empty:
            return

        filter = b""
        if self.hypnoxv2_tweet_filter:
            filter = self.hypnoxv2_tweet_filter.encode("unicode_escape")

        tweets = pandas.DataFrame(
            HypnoxTweet.select()
            .where(HypnoxTweet.time >= pending.iloc[0].time)
            .where(HypnoxTweet.text.iregexp(filter))
            .dicts()
        )

        if tweets.empty:
            return

        tweets.text = tweets.text.apply(standardize)
        freq = get_timeframe_freq(self.timeframe)
        tweets = tweets.drop_duplicates("text")
        tweets = tweets.drop("id", axis=1)
        tweets = tweets.set_index("time")

        unigrams = Hypnoxv2Gram.get_by_rank(1)
        if unigrams.empty:
            raise DisablingError("no unigrams found")
            return
        unigrams = unigrams.loc[unigrams.label == 1].index.tolist()

        bigrams = Hypnoxv2Gram.get_by_rank(2)
        if bigrams.empty:
            raise DisablingError("no bigrams found")
        pos_bigrams = bigrams[bigrams.label == 1]
        neg_bigrams = bigrams[bigrams.label == -1]

        tqdm.pandas()
        tweets = tweets.text.groupby([pandas.Grouper(freq=freq)]).progress_apply(
            lambda x: aggregate_tweets(x, pos_bigrams, neg_bigrams, unigrams)
        )

        pending["signal"] = NEUTRAL

        pending = pending.set_index("time")
        pending["score"] = tweets
        pending.score.fillna(0, inplace=True)

        pending = pending.reset_index()

        pending.loc[pending["score"] > self.hypnoxv2_upper_threshold, "signal"] = BUY

        pending.loc[pending["score"] < self.hypnoxv2_lower_threshold, "signal"] = SELL

        return pending
