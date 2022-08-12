import datetime
import logging
import sys

import matplotlib.pyplot as plt
import numpy
import pandas
import peewee
import talib.abstract as ta

import src as hypnox

# min_roi
# stop_loss


def backtest(args):
    start = datetime.datetime(2020, 7, 1)
    end = datetime.datetime(2022, 7, 1)

    prices_q = hypnox.db.Price.select().where((hypnox.db.Price.time > start)
                                              & (hypnox.db.Price.time < end))
    prices = pandas.DataFrame(prices_q.dicts()).set_index("time")

    timegroup = peewee.fn.DATE_TRUNC("day", hypnox.db.Tweet.time)
    filter = (hypnox.db.Tweet.time > start) \
        & (hypnox.db.Tweet.time < end) \
        & (hypnox.db.Tweet.intensity > 0.08) \
        & (hypnox.db.Tweet.text.iregexp(r"btc|bitcoin"))

    # TODO: if intensity should be mostly 0, why filter it here?
    # it shouldn't change much of the std dev

    stddev = peewee.fn.STDDEV(hypnox.db.Tweet.intensity)
    delta = stddev - peewee.fn.LAG(stddev).over(order_by=timegroup)
    intensities_q = hypnox.db.Tweet.select(
        timegroup.alias("time"), delta.alias("intensity")).where(
            filter
            & (hypnox.db.Tweet.model_i == "i20220811")).group_by(1)
    intensities = pandas.DataFrame(intensities_q.dicts())
    cur = hypnox.db.connection.cursor()
    print(cur.mogrify(*intensities_q.sql()).decode('utf-8'))

    if intensities.empty:
        logging.error("empty intensity scores")
        sys.exit(1)

    # sum = peewee.fn.SUM(hypnox.db.Tweet.polarity)
    # polarities_q = hypnox.db.Tweet.select(
    #     timegroup.alias("time"), sum.alias("polarity")).where(
    #         filter
    #         & (hypnox.db.Tweet.model_p == "p20220802")).group_by(1)
    # polarities = pandas.DataFrame(polarities_q.dicts())

    # if polarities.empty:
    #     logging.error("empty polarity scores")
    #     sys.exit(1)

    intensities = intensities.set_index("time").resample("4H").ffill()
    # polarities = polarities.set_index("time").resample("4H").ffill()
    prices["intensity"] = intensities["intensity"]
    # prices["polarity"] = polarities["polarity"]

    # buy = ((prices["intensity"] > 0.1) & (prices["polarity"] > 0))
    # prices.loc[buy, "buy"] = 1
    # sell = ((prices["intensity"] > 0.1) & (prices["polarity"] < 0))
    # prices.loc[sell, "sell"] = 1

    short_avg = ta.EMA(prices, timeperiod=2)
    long_avg = ta.EMA(prices, timeperiod=17)
    prices["trend"] = False
    prices.loc[(short_avg > long_avg), "trend"] = True

    prices.reset_index(inplace=True)

    x = numpy.arange(0, len(prices))
    fig, ax = plt.subplots(1, figsize=(12, 6))
    for idx, val in prices.iterrows():
        plt.plot([x[idx], x[idx]], [val["low"], val["high"]])
    plt.show()
