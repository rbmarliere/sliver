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


def get_timeframe_delta(timeframe):
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

    return datetime.timedelta(seconds=timeframes[timeframe])


def truncate(f, n):
    '''Truncates/pads a float f to n decimal places without rounding'''
    # https://stackoverflow.com/questions/783897/how-to-truncate-float-values
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return float('{0:.{1}f}'.format(f, n))
    i, p, d = s.partition('.')
    return float('.'.join([i, (d + '0' * n)[:n]]))


def get_mean_var(series: pandas.DataFrame,
                 n: int,
                 old_mean: decimal.Decimal,
                 old_var: decimal.Decimal):
    # https://math.stackexchange.com/questions/102978/incremental-computation-of-standard-deviation
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
    return strat.market.quote.format(x[column])


def bformat(x, column):
    strat = core.db.Strategy.get_by_id(x.strategy_id)
    return strat.market.quote.format(x[column])


def sformat(x):
    strat = core.db.Strategy.get_by_id(x.strategy_id)
    return strat.market.get_symbol()

# import nltk
# try:
#     nltk.data.find("corpora/stopwords.zip")
#     nltk.data.find("corpora/wordnet.zip")
#     nltk.data.find("corpora/omw-1.4.zip")
# except LookupError:
#     nltk.download("stopwords")
#     nltk.download("wordnet")
#     nltk.download("omw-1.4")

# TO_KEEP_STOPWORDS = [
#     "this", "that'll", "these", "having", "does", "doing", "until", "while",
#     "about", "against", "between", "into", "through", "during", "before",
#     "after", "above", "below", "from", "up", "down", "in", "out", "on", "off",
#     "over", "under", "again", "further", "then", "once", "here", "there",
#     "when", "few", "both", "more", "most", "other", "some", "than", "too",
#     "very", "can", "will", "should", "should've", "now", "ain", "aren",
#     "aren't", "could", "couldn", "couldn't", "didn", "didn't", "doesn",
#     "doesn't", "hadn", "hadn't", "hasn", "hasn't", "haven", "haven't", "isn",
#     "isn't", "mighn", "mightn't", "mustn", "mustn't", "needn", "needn't",
#     "shan", "shan't", "shouldn", "shouldn't", "wasn", "wasn't", "weren",
#     "weren't", "won'", "won't", "wouldn", "wouldn't", "if"
# ]

# nltkstops = set(nltk.corpus.stopwords.words("english"))
# stops = [w for w in nltkstops if w not in TO_KEEP_STOPWORDS]

# lem = nltk.stem.wordnet.WordNetLemmatizer()

# def standardize(text):
#     # convert to lower case
#     text = text.lower()
#     # remove carriages and tabs
#     text = re.sub(r"(\n|\r|\t)", " ", text)
#     text = text.strip()
#     # remove links
#     text = re.sub(r"http\S+", "", text)
#     # remove hashtags, usernames and html entities
#     text = re.sub(r"(#|@|&|\$)\S+", "", text)
#     # remove punctuation
#     text = re.sub(r"[%s]" % re.escape(string.punctuation), " ", text)
#     # remove some stopwords
#     text = re.sub(r"\b(" + "|".join(stops) + r")\b\s*", "", text)
#     # keep only letters
#     text = re.sub(r"[^a-zA-Z]", " ", text)
#     # keep only words with more than 2 characters
#     text = re.sub(r"\b\S\S?\b", "", text)
#     # remove excess white spaces
#     text = re.sub(r" +", " ", text)
#     # remove leading and trailing white spaces
#     text = text.strip()
#
#     # keep only sentences with four words minimum
#     if len(text.split()) >= 4:
#         # lemmatize each word
#         text = " ".join([lem.lemmatize(w) for w in text.split()])
#         return text
#     else:
#         return None
