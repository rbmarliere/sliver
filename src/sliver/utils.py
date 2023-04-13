import datetime
import logging.handlers
import re
import time
from decimal import Decimal as D

import pandas
from flask_restful import fields

from sliver.config import Config


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
        "1w",
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
        "1w": "W-MON",
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


def get_next_refresh(interval_in_minutes):
    now = datetime.datetime.utcnow()
    freq = f"{interval_in_minutes}T"
    last = now.replace(minute=0, second=0, microsecond=0)
    range = pandas.date_range(last, periods=61, freq=freq)
    series = range.to_series().asfreq(freq)
    next_refresh = series.loc[series > now].iloc[0]

    return next_refresh


def get_return(entry_price, exit_price):
    return D(str(((exit_price / entry_price) - 1) * 100)).quantize(D("0.0001"))


def get_roi(entry_cost, pnl):
    return D(str((pnl / entry_cost) * 100)).quantize(D("0.0001"))


def quantize(row, col, prec_col):
    if row[col] is None:
        return row[col]

    return row[col].quantize(D("10") ** (D("-1") * row[prec_col]))


def get_logger(log, suppress_output=False):
    log_file = f"{Config().LOGS_DIR}/{log}.log"

    formatter = logging.Formatter("%(asctime)s -- %(message)s")
    formatter.converter = time.gmtime

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=52428800, backupCount=32  # 50mb
    )
    file_handler.setFormatter(formatter)

    log = logging.getLogger(log)
    log.setLevel(logging.INFO)
    log.addHandler(file_handler)

    if suppress_output:
        return log

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)

    return log


def parse_field_type(field_type):
    if field_type == bool:
        return fields.Boolean
    elif field_type == datetime.datetime:
        return fields.DateTime(dt_format="iso8601")
    elif field_type == float or field_type == D:
        return fields.Float
    elif field_type == int:
        return fields.Integer
    elif field_type == str:
        return fields.String
    else:
        return fields.Raw
