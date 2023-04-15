import nltk
import pandas
import peewee
from tqdm import tqdm

import sliver.database as db
from sliver.config import Config
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


class Hypnoxv2Bigram(db.BaseModel):
    ...


class Hypnoxv2Unigram(db.BaseModel):
    ...


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
        db.connection.create_tables([Hypnoxv2Strategy, Hypnoxv2Indicator])

    def refresh_indicators(self, indicators):
        BUY = StrategySignals.BUY
        NEUTRAL = StrategySignals.NEUTRAL
        SELL = StrategySignals.SELL

        filter = b""
        if self.hypnoxv2_tweet_filter:
            filter = self.hypnoxv2_tweet_filter.encode("unicode_escape")

        tweets = pandas.DataFrame(
            HypnoxTweet.select()
            .where(HypnoxTweet.time >= indicators.iloc[0].time)
            .where(HypnoxTweet.text.iregexp(filter))
            .dicts()
        )

        if tweets.empty:
            return

        indicators = indicators.loc[indicators.time >= tweets.time.min()].copy()

        if indicators.empty:
            return

        tweets.text = tweets.text.apply(standardize)
        freq = get_timeframe_freq(self.timeframe)
        tweets = tweets.drop_duplicates("text")
        tweets = tweets.drop("id", axis=1)
        tweets = tweets.set_index("time")

        unigrams = pandas.read_csv(f"{Config().ETC_DIR}/unigrams.tsv", sep="\t")
        unigrams = unigrams.loc[unigrams.label == 1].unigram.tolist()

        bigrams = pandas.read_csv(
            f"{Config().ETC_DIR}/bigrams.tsv", sep="\t"
        ).set_index("bigram")

        pos_bigrams = bigrams[bigrams.label == 1]
        neg_bigrams = bigrams[bigrams.label == -1]

        tqdm.pandas()
        tweets = tweets.text.groupby([pandas.Grouper(freq=freq)]).progress_apply(
            lambda x: aggregate_tweets(x, pos_bigrams, neg_bigrams, unigrams)
        )

        indicators["signal"] = NEUTRAL

        indicators = indicators.set_index("time")
        indicators["score"] = tweets

        indicators = indicators.dropna(subset="score")

        if indicators.empty:
            return

        indicators.loc[
            indicators["score"] > self.hypnoxv2_upper_threshold, "signal"
        ] = BUY

        indicators.loc[
            indicators["score"] < self.hypnoxv2_lower_threshold, "signal"
        ] = SELL

        Indicator.insert_many(
            indicators[["strategy", "price", "signal"]].to_dict("records")
        ).execute()

        first = indicators[["strategy", "price", "signal"]].iloc[0]
        first_id = Indicator.get(**first.to_dict()).id
        indicators.indicator = range(first_id, first_id + len(indicators))

        Hypnoxv2Indicator.insert_many(
            indicators[["indicator", "score"]].to_dict("records")
        ).execute()
