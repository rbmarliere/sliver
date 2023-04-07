import pandas
import decimal

from sliver.utils import get_timeframe_freq


def get_mean_var(
    series: pandas.DataFrame,
    n: int,
    old_mean: decimal.Decimal,
    old_var: decimal.Decimal,
):
    # https://math.stackexchange.com/questions/102978/incremental-computation-of-standard-deviation
    n = decimal.Decimal(str(n))
    for i, x in series.items():
        try:
            x = decimal.Decimal(str(x))
        except decimal.InvalidOperation:
            x = 0

        n += 1

        new_mean = (old_mean * (n - 1) + x) / n

        if n == 1:
            new_var = 0
        else:
            new_var = (
                (n - 2) * old_var
                + (n - 1) * (old_mean - new_mean) ** 2
                + (x - new_mean) ** 2
            ) / (n - 1)

        old_var = new_var
        old_mean = new_mean

    return new_mean, new_var


def HYPNOX(ohlc, tweets, timeframe="1h", n_samples=0, mean=0, variance=0):
    indicators = ohlc.set_index("time").copy()

    tweets_c = len(tweets)

    if tweets.empty:
        indicators["z_score"] = 0
        indicators["n_samples"] = n_samples
        indicators["mean"] = mean
        indicators["variance"] = variance
        return indicators

    # compute new metrics
    mean, variance = get_mean_var(tweets.score, n_samples, mean, variance)

    # apply normalization
    tweets = tweets.set_index("time")
    tweets["z_score"] = (tweets.score - mean) / variance.sqrt()

    # resample tweets by strat timeframe freq median
    freq = get_timeframe_freq(timeframe)
    tweets = tweets[["z_score"]].resample(freq, label="right").median().ffill()

    # check if z_score is already in indicators
    if "z_score" in indicators.columns:
        indicators = indicators.drop("z_score", axis=1)

    # join both dataframes
    indicators = pandas.concat([indicators, tweets], join="inner", axis=1)

    # fill out remaining columns
    indicators["n_samples"] = n_samples + tweets_c
    indicators["mean"] = mean
    indicators["variance"] = variance

    indicators = indicators.reset_index()

    return indicators
