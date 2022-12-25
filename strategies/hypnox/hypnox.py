import pandas
import peewee

import core
import models
from strategies.hypnox.replay import replay


class HypnoxTweet(core.db.BaseModel):
    time = peewee.DateTimeField()
    text = peewee.TextField()

    def get_tweets_by_model(model: str):
        return HypnoxTweet \
            .select(HypnoxTweet, HypnoxScore) \
            .join(HypnoxScore,
                  peewee.JOIN.LEFT_OUTER,
                  on=((HypnoxScore.tweet_id == HypnoxTweet.id)
                      & (HypnoxScore.model == model))) \
            .order_by(HypnoxTweet.time)


class HypnoxScore(core.db.BaseModel):
    tweet = peewee.ForeignKeyField(HypnoxTweet)
    model = peewee.TextField()
    score = peewee.DecimalField()

    class Meta:
        constraints = [peewee.SQL("UNIQUE (tweet_id, model)")]


class HypnoxIndicator(core.db.BaseModel):
    indicator = peewee.ForeignKeyField(core.db.Indicator)
    i_score = peewee.DecimalField()
    i_mean = peewee.DecimalField()
    i_variance = peewee.DecimalField()
    p_score = peewee.DecimalField()
    p_mean = peewee.DecimalField()
    p_variance = peewee.DecimalField()
    n_samples = peewee.IntegerField()


class HypnoxStrategy(core.db.BaseModel):
    strategy = peewee.ForeignKeyField(core.db.Strategy)
    i_threshold = peewee.DecimalField(default=0)
    p_threshold = peewee.DecimalField(default=0)
    tweet_filter = peewee.TextField(default="")
    model_i = peewee.TextField(null=True)
    model_p = peewee.TextField(null=True)

    def get_indicators(self):
        return self.strategy \
            .get_indicators() \
            .select(core.db.Price, core.db.Indicator, HypnoxIndicator) \
            .join(HypnoxIndicator, peewee.JOIN.LEFT_OUTER)

    def refresh(self):
        # update tweet scores
        if self.model_i:
            model_i = models.load(self.model_i)
            replay(model_i)
        if self.model_p:
            model_p = models.load(self.model_p)
            replay(model_p)

        self.refresh_indicators()

    def refresh_indicators(self):
        # grab indicators
        indicators_q = self.get_indicators()
        indicators = pandas.DataFrame(indicators_q.dicts())

        # filter relevant data
        self_regex = self.tweet_filter.encode("unicode_escape")
        f = HypnoxTweet.text.iregexp(self_regex)
        f = f & (HypnoxScore.model.is_null(False))
        existing = indicators.dropna()
        indicators = indicators[indicators.isnull().any(axis=1)]
        if indicators.empty:
            core.watchdog.info("indicator data is up to date")
            return 0
        f = f & (HypnoxTweet.time > indicators.iloc[0].time)

        # grab scores
        intensities_q = HypnoxTweet.get_tweets_by_model(self.model_i).where(f)
        polarities_q = HypnoxTweet.get_tweets_by_model(self.model_p).where(f)
        if intensities_q.count() == 0 or polarities_q.count() == 0:
            core.watchdog.info("indicator data is up to date")
            return 0

        intensities = pandas.DataFrame(intensities_q.dicts())
        intensities = intensities.rename(columns={"score": "intensity"})
        intensities = intensities.set_index("time")

        # grab polarities
        polarities = pandas.DataFrame(polarities_q.dicts())
        polarities = polarities.rename(columns={"score": "polarity"})
        polarities = polarities.set_index("time")

        # build tweets dataframe
        tweets = pandas.concat([intensities, polarities], axis=1)
        if tweets.empty:
            core.watchdog.info("indicator data is up to date")
            return 0
        tweets = tweets[["intensity", "polarity"]]

        # grab last computed metrics
        if existing.empty:
            n_samples = 0
            i_mean = 0
            p_mean = 0
            i_variance = 0
            p_variance = 0
        else:
            n_samples = existing.iloc[-1].n_samples
            i_mean = existing.iloc[-1].i_mean
            p_mean = existing.iloc[-1].p_mean
            i_variance = existing.iloc[-1].i_variance
            p_variance = existing.iloc[-1].p_variance

        # compute new metrics
        i_mean, i_variance = core.utils.get_mean_var(tweets.intensity,
                                                     n_samples,
                                                     i_mean,
                                                     i_variance)
        p_mean, p_variance = core.utils.get_mean_var(tweets.polarity,
                                                     n_samples,
                                                     p_mean,
                                                     p_variance)

        # apply normalization
        tweets["i_score"] = (tweets.intensity - i_mean) / i_variance.sqrt()
        tweets["p_score"] = (tweets.polarity - p_mean) / p_variance.sqrt()

        # resample tweets by strat timeframe freq median
        freq = core.utils.get_timeframe_freq(self.strategy.timeframe)
        tweets = tweets[["i_score", "p_score"]].resample(freq).median().ffill()

        # join both dataframes
        indicators = indicators.set_index("time")
        indicators = indicators.drop("i_score", axis=1)
        indicators = indicators.drop("p_score", axis=1)
        indicators = pandas.concat([indicators, tweets], join="inner", axis=1)
        if indicators.empty:
            core.watchdog.info("indicator data is up to date")
            return 0

        # fill out remaining columns
        indicators = indicators.drop("price", axis=1)
        indicators.strategy = self.strategy.id
        indicators.n_samples = n_samples + len(tweets)
        indicators.i_mean = i_mean
        indicators.i_variance = i_variance
        indicators.p_mean = p_mean
        indicators.p_variance = p_variance

        # compute signals
        indicators["signal"] = "neutral"
        buy_rule = ((indicators["i_score"] > self.i_threshold) &
                    (indicators["p_score"] > self.p_threshold))
        indicators.loc[buy_rule, "signal"] = "buy"
        sell_rule = ((indicators["i_score"] > self.i_threshold) &
                     (indicators["p_score"] < self.p_threshold))
        indicators.loc[sell_rule, "signal"] = "sell"

        # reset index
        indicators = indicators.reset_index()

        with core.db.connection.atomic():
            indicators = indicators.rename(columns={
                "id": "price_id",
                "strategy": "strategy_id",
            })
            vanilla_indicators = indicators[[
                "strategy_id",
                "price_id",
                "signal",
            ]]
            core.db.Indicator.insert_many(
                vanilla_indicators.to_dict("records")).execute()

            hypnox_indicators = indicators[[
                "i_score",
                "i_mean",
                "i_variance",
                "p_score",
                "p_mean",
                "p_variance",
                "n_samples"
            ]]
            first_id = core.db.Indicator.get(
                **vanilla_indicators.iloc[0].to_dict()).id
            hypnox_indicators.insert(0,
                                     "indicator_id",
                                     range(first_id,
                                           first_id + len(indicators)))
            HypnoxIndicator.insert_many(
                hypnox_indicators.to_dict("records")).execute()
