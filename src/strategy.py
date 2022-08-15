import datetime

import pandas
import peewee

import src as hypnox

# import talib.abstract as ta

min_roi = 0.05
stop_loss = -0.025
position_size = 1


def backtest(args):
    start = datetime.datetime(2020, 7, 1)
    end = datetime.datetime(2022, 7, 1)

    prices_q = hypnox.db.Price.select().where((hypnox.db.Price.time > start)
                                              & (hypnox.db.Price.time < end))
    prices = pandas.DataFrame(prices_q.dicts()).set_index("time")

    timegroup = peewee.fn.DATE_TRUNC("day", hypnox.db.Tweet.time)
    filter = (hypnox.db.Tweet.time > start) \
        & (hypnox.db.Tweet.time < end) \
        & (hypnox.db.Tweet.text.iregexp(r"btc|bitcoin"))

    stddev = peewee.fn.STDDEV(hypnox.db.Tweet.intensity)
    delta = stddev - peewee.fn.LAG(stddev).over(order_by=timegroup)
    intensities_q = hypnox.db.Tweet.select(
        timegroup.alias("time"), delta.alias("intensity")).where(
            filter
            & (hypnox.db.Tweet.model_i == "i20220811")).group_by(1)
    intensities = pandas.DataFrame(intensities_q.dicts())

    # sum = peewee.fn.SUM(hypnox.db.Tweet.polarity)
    # polarities_q = hypnox.db.Tweet.select(
    #     timegroup.alias("time"), sum.alias("polarity")).where(
    #         filter
    #         & (hypnox.db.Tweet.model_p == "p20220802")).group_by(1)
    # polarities = pandas.DataFrame(polarities_q.dicts())

    intensities = intensities.set_index("time").resample("4H").ffill()
    # polarities = polarities.set_index("time").resample("4H").ffill()
    prices["intensity"] = intensities["intensity"]
    # prices["polarity"] = polarities["polarity"]

    buys = prices.loc[(prices["intensity"] < 0.026)]

    # prices.loc[buy, "buy"] = 1
    # sell = (prices["intensity"] < 0.1)
    # sell = ((prices["intensity"] > 0.1) & (prices["polarity"] < 0))
    # prices.loc[sell, "sell"] = 1

    # short_avg = ta.EMA(prices, timeperiod=2)
    # long_avg = ta.EMA(prices, timeperiod=17)
    # prices["trend"] = False
    # prices.loc[(short_avg > long_avg), "trend"] = True

    # compute entries
    positions = []
    for i, row in buys.iterrows():
        positions.append(
            hypnox.db.Position(market="BTC/USDT",
                               size=position_size,
                               amount=position_size * row["open"],
                               entry_time=i,
                               entry_price=row["open"]))

    # compute exits
    hypnox.db.Position.drop_table()
    hypnox.db.Position.create_table()
    total_pnl = 0
    for position in positions:
        for time, row in prices.loc[position.entry_time:].iterrows():
            price_delta = row["open"] - position.entry_price

            tmp_roi = price_delta / position.amount

            if tmp_roi >= min_roi or tmp_roi <= stop_loss:
                total_pnl += price_delta
                position.exit_time = time
                position.exit_price = row["open"]
                position.pnl = price_delta
                position.save()
                break

    print("")


#  MOON INDICATORS
# moon = pylunar.MoonInfo((28,2,4.9),(86,55,0.9))
# def time_to_full_moon(moon, date):
# 	moon.update(date)
# 	return moon.time_to_full_moon() * 24
# dataframe["time_to_full_moon"] =
# dataframe["date"].apply( lambda x: time_to_full_moon(moon, x) )
# def time_to_new_moon(moon, date):
# 	moon.update(date)
# 	return moon.time_to_new_moon()
# dataframe["time_to_new_moon"] =
# dataframe["date"].apply( lambda x: time_to_new_moon(moon, x) )

#  MOON PERIODS
# def period(moon, date):
# 	moon.update(date)
# 	nm_sec = moon.time_to_new_moon()*60*60
# 	if nm_sec - 1031220 <= 0 and nm_sec - 564020 > 0:
# 		# green
# 		return 1.12
# 	if nm_sec - 564020 <= 0 and nm_sec - 298620 > 0:
# 		# black
# 		return 0.78
# 	if nm_sec - 298620 <= 0 and nm_sec - 298620 + 612000 > 0:
# 		# green
# 		return 1.12
# 	if nm_sec - 1819620 <= 0 and nm_sec - 1531920 >= 0:
# 		# yellow
# 		return 1.22
# 	# red is remainder
# 	return 0.93
# dataframe["moon_period"] =
# dataframe["date"].apply( lambda x: period(moon, x) )

# dataframe["res2sup"] =
# ( dataframe["resistance"] / dataframe["support"] ) * dataframe["moon_period"]

#  todo: idea is a dynamic stoploss. probably not possible
# moon.update(datetime.datetime.now())
# black_start = 574020
# black_end = 298620
# nm_sec = moon.time_to_new_moon()*60*60
# self.stoploss = self.STOPLOSS_DEFAULT
# if nm_sec - black_start >= 0 and nm_sec - black_end >= 0:
# 	self.stoploss = self.stoploss / 2
# print(moon.time_to_new_moon())
# print(nm_sec)
