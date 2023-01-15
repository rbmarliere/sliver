import datetime
import decimal
import re

import pandas

import core


def standardize(text):
    # convert to lower case
    text = text.lower()
    # remove carriages and tabs
    text = re.sub(r"(\n|\r|\t)", " ", text)
    text = text.strip()
    # remove links
    text = re.sub(r"http\S+", "", text)
    # remove hashtags, usernames and html entities
    text = re.sub(r"(#|@|&|\$)\S+", "", text)

    return text


def get_timeframes():
    return [
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w"
    ]


def get_timeframe_freq(timeframe):
    # convert candle timeframe to pandas freq
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.dt.floor.html
    # https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases
    timeframes = {
        "1m": "1T",
        "3m": "3T",
        "5m": "5T",
        "15m": "15T",
        "30m": "30T",
        "1h": "1H",
        "2h": "2H",
        "4h": "4H",
        "6h": "6H",
        "8h": "8H",
        "12h": "12H",
        "1d": "1D",
        "3d": "3D",
        "1w": "W-MON"
    }

    assert timeframe in timeframes, "timeframe not supported"

    return timeframes[timeframe]


def get_timeframe_in_seconds(timeframe):
    timeframes = {
        "1m": 1 * 60,
        "3m": 3 * 60,
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 1 * 60 * 60,
        "2h": 2 * 60 * 60,
        "4h": 4 * 60 * 60,
        "6h": 6 * 60 * 60,
        "8h": 8 * 60 * 60,
        "12h": 12 * 60 * 60,
        "1d": 1 * 24 * 60 * 60,
        "3d": 3 * 24 * 60 * 60,
        "1w": 7 * 24 * 60 * 60,
    }

    assert timeframe in timeframes, "timeframe not supported"

    return timeframes[timeframe]


def get_timeframe_delta(timeframe):
    return datetime.timedelta(seconds=get_timeframe_in_seconds(timeframe))


def get_mean_var(series: pandas.DataFrame,
                 n: int,
                 old_mean: decimal.Decimal,
                 old_var: decimal.Decimal):
    # https://math.stackexchange.com/questions/102978/incremental-computation-of-standard-deviation
    n = decimal.Decimal(str(n))
    for i, x in series.items():
        x = decimal.Decimal(str(x))
        n += 1

        new_mean = (old_mean*(n-1) + x) / n

        if n == 1:
            new_var = 0
        else:
            new_var = ((n-2)*old_var + (n-1)*(old_mean - new_mean)
                       ** 2 + (x - new_mean)**2) / (n-1)

        old_var = new_var
        old_mean = new_mean

    return new_mean, new_var


def qformat(x, column):
    strat = core.db.Strategy.get_by_id(x.strategy_id)

    prec = None
    if strat.market.price_precision > 0:
        prec = strat.market.price_precision

    return strat.market.quote.format(x[column], prec=prec)


def bformat(x, column):
    strat = core.db.Strategy.get_by_id(x.strategy_id)

    prec = None
    if strat.market.amount_precision > 0:
        prec = strat.market.amount_precision

    return strat.market.base.format(x[column], prec=prec)


def sformat(x):
    strat = core.db.Strategy.get_by_id(x.strategy_id)
    return strat.market.get_symbol()
