import datetime

import hypnox.watchdog.log
import pandas
import peewee

import src as hypnox

# import talib.abstract as ta


def get_indicators(strategy):
    timegroup = peewee.fn.DATE_TRUNC("hour", hypnox.db.Tweet.time)
    filter = hypnox.db.Tweet.text.iregexp(
        strategy["TWEET_FILTER"].encode("unicode_escape"))

    # z-score = valor presente - media da amostra / stddev da amostra
    # media do z-score (caso haja varios fatores Z)
    stddev = peewee.fn.STDDEV(hypnox.db.Tweet.intensity)
    delta = stddev - peewee.fn.LAG(stddev).over(order_by=timegroup)
    intensities_q = hypnox.db.Tweet.select(
        timegroup.alias("time"), delta.alias("intensity")).where(
            filter
            & (hypnox.db.Tweet.model_i == strategy["I_MODEL"])).group_by(1)
    indicators = pandas.DataFrame(intensities_q.dicts())

    # if indicators.empty:
    #     raise Exception

    sum = peewee.fn.SUM(hypnox.db.Tweet.polarity)
    polarities_q = hypnox.db.Tweet.select(
        timegroup.alias("time"), sum.alias("polarity")).where(
            filter
            & (hypnox.db.Tweet.model_p == strategy["P_MODEL"])).group_by(1)
    polarities = pandas.DataFrame(polarities_q.dicts())

    # if polarities.empty:
    #     raise Exception

    indicators["polarity"] = polarities

    return indicators.set_index("time")


def get_signal(strategy, indicators):
    # TODO weighthing, e.g.
    # 20% * swapperbox + 80% * hypnox_AI + 10% *
    # traditional_TA + 10% * chain_data

    # buys = prices.loc[(prices["intensity"] < 0.026)]
    # prices.loc[buy, "buy"] = 1
    # sell = (prices["intensity"] < 0.1)
    # sell = ((prices["intensity"] > 0.1) & (prices["polarity"] < 0))
    # prices.loc[sell, "sell"] = 1

    # short_avg = ta.EMA(prices, timeperiod=2)
    # long_avg = ta.EMA(prices, timeperiod=17)
    # prices["trend"] = False
    # prices.loc[(short_avg > long_avg), "trend"] = True
    # TODO maybe "sell_half" or something like that?
    # TODO chart pattern recognition ?

    # if (curr_intensity > INTENSITY_THRESHOLD
    #         and curr_polarity > POLARITY_THRESHOLD):
    #     return "buy"
    # elif (curr_intensity > INTENSITY_THRESHOLD
    #       and curr_polarity < POLARITY_THRESHOLD):
    #     return "sell"
    # else:
    #     return "neutral"

    import random
    i = random.randint(0, 100)
    if i > 80:
        hypnox.watchdog.log.info("received buy signal")
        return "buy"
    elif i < 20:
        hypnox.watchdog.log.info("received sell signal")
        return "sell"
    else:
        hypnox.watchdog.log.info("received neutral signal")
        return "neutral"


def backtest(args):
    start = datetime.datetime(2020, 7, 1)
    end = datetime.datetime(2022, 7, 1)

    strategy = hypnox.config.StrategyConfig(args.strategy).config
    indicators = get_indicators(strategy)
    indicators = indicators.resample("4H").ffill()

    prices_q = hypnox.db.Price.select().where((hypnox.db.Price.time > start)
                                              & (hypnox.db.Price.time < end))
    prices = pandas.DataFrame(prices_q.dicts()).set_index("time")
    prices["intensity"] = indicators["intensity"]
    # prices["polarity"] = indicators["polarity"]
    # prices["ta-lib"] =

    buys = []
    for i, p in prices.iterrows():
        signal = get_signal(p)
        if signal == "buy":
            buys[i] = p

    target_cost = 10000

    # compute entries
    positions = []
    for i, buy in buys:
        positions.append(
            hypnox.db.Position(symbol="BTCUSDT",
                               status="closed",
                               entry_cost=target_cost,
                               entry_amount=target_cost / buy["open"],
                               entry_price=buy["open"],
                               entry_time=i))

    # compute exits
    total_pnl = 0
    for position in positions:
        for time, row in prices.loc[position.entry_time:].iterrows():
            # TODO fix arg
            signal = get_signal(row)
            price_delta = row["open"] - position.entry_price
            tmp_roi = price_delta / position.amount
            if (tmp_roi >= strategy["MINIMUM_ROI"]
                    or tmp_roi <= strategy["STOP_LOSS"] or signal == "sell"):
                total_pnl += price_delta
                position.exit_time = time
                position.exit_price = row["open"]
                position.pnl = price_delta
                break

    hypnox.watchdog.log.info("PnL: " + str(round(total_pnl, 2)))
    hypnox.watchdog.log.info("ROI: " +
                             str(round((total_pnl / target_cost) - 1, 2)))


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

#  TODO idea is a dynamic stoploss. probably not possible
# moon.update(datetime.datetime.now())
# black_start = 574020
# black_end = 298620
# nm_sec = moon.time_to_new_moon()*60*60
# self.stoploss = self.STOPLOSS_DEFAULT
# if nm_sec - black_start >= 0 and nm_sec - black_end >= 0:
# 	self.stoploss = self.stoploss / 2
# print(moon.time_to_new_moon())
# print(nm_sec)
