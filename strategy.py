import collections
import datetime
import freqtrade
import numpy
import os
import pandas
import pylunar
import talib.abstract as ta
import pytz
from sklearn import preprocessing

class hypnox(freqtrade.strategy.interface.IStrategy):
	INTERFACE_VERSION = 2
	minimal_roi = { "0": 100 } # disabled
	stoploss = -100.0 # disabled

	plot_config = {
		"main_plot": {
			#"support": {},
			#"resistance": {},
		},
		"subplots": {
			#"res2sup": {
			#	"res2sup": { },
			#},
			"ema": {
				"short": { },
				"long": { },
			},
			#"moon": {
			#	"time_to_full_moon": { },
			#	"time_to_new_moon": { },
			#},
			"tacitus": {
				"tacitus": { },
			},
			"srsi_k": {
				"srsi_k": { },
				"srsi_d": { },
			}
		}
	}

	def populate_indicators(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		# CLASSIC TECHNICAL INDICATORS
		dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

		period = 14
		smoothd = 3
		smoothk = 3
		stochrsi  = (dataframe["rsi"] - dataframe["rsi"].rolling(period).min()) / (dataframe["rsi"].rolling(period).max() - dataframe["rsi"].rolling(period).min())
		dataframe["srsi_k"] = stochrsi.rolling(smoothk).mean() * 100
		dataframe["srsi_d"] = dataframe["srsi_k"].rolling(smoothd).mean()

		dataframe["short"] = ta.EMA(dataframe, timeperiod=2)
		dataframe["long"] = ta.EMA(dataframe, timeperiod=5)

		# TACITUS INDICATOR
		dateformat = "%Y%m%d_%H"
		if self.timeframe == "1d":
			dateformat = "%Y%m%d"

		# load concious tally
		tally_dir = os.path.dirname(os.path.realpath(__file__)) + "/data/tally"
		for filename in os.listdir(tally_dir):
			if filename.startswith("."):
				continue
			tally_date = datetime.datetime.strptime(filename, dateformat).replace(tzinfo=pytz.UTC)
			tally_result = pandas.read_csv(tally_dir + "/" + filename)
			dataframe.loc[ dataframe["date"] == tally_date, "tacitus_tally" ] = tally_result["neg"][0] - tally_result["pos"][0]

		# load unconscious tally
		parse_dir = os.path.dirname(os.path.realpath(__file__)) + "/data/parse"
		for filename in sorted(os.listdir(parse_dir)):
			if filename.startswith("."):
				continue
			basename, extension = os.path.splitext(filename)
			if extension != "":
				continue
			parse_date = datetime.datetime.strptime(filename, dateformat).replace(tzinfo=pytz.UTC)
			parse_result = pandas.read_csv(parse_dir + "/" + filename)
			dataframe.loc[ dataframe["date"] == parse_date, "tacitus_signal" ] = parse_result["signal"][0]

		# normalize
		scaler = preprocessing.MinMaxScaler()
		dataframe["tacitus_signal"] = scaler.fit_transform(dataframe[["tacitus_signal"]])
		dataframe["tacitus_tally"] = scaler.fit_transform(dataframe[["tacitus_tally"]])
		dataframe["tacitus"] = dataframe["tacitus_signal"] - dataframe["tacitus_tally"]
		dataframe["tacitus"] = scaler.fit_transform(dataframe[["tacitus"]])

		# RESISTANCE TO SUPPORT RATIO INDICATOR
		short_avg = ta.EMA(dataframe, timeperiod=2)
		long_avg = ta.EMA(dataframe, timeperiod=17)

		dataframe["trend"] = False
		dataframe.loc[ ( short_avg > long_avg ), "trend"] = True

		dataframe.insert(0, "cycle", 0)
		count = 0
		begin = dataframe["date"].iloc[0]
		last_candle = dataframe.iloc[0]
		for i, (idx, candle) in enumerate(dataframe.iterrows()):
			if candle["trend"] != last_candle["trend"]:
				dataframe.loc[ ( dataframe["date"] >= begin ) & ( dataframe["date"] < candle["date"] ), "cycle" ] = count
				begin = candle["date"]
				count += 1
			if i == len(dataframe) - 1:
				dataframe.loc[ ( dataframe["date"] >= begin ), "cycle"] = count
			last_candle = candle

		dataframe.insert(0, "support", 0)
		dataframe.insert(0, "resistance", 0)
		for idx, candle in dataframe.iterrows():
			if candle["cycle"] < 4:
				continue

			support = 0
			last_cycles = [ 0, -1, -3 ] if candle["trend"] else [ 0, -2, -4 ]
			for i in last_cycles:
				support += dataframe[ dataframe["cycle"] == candle["cycle"] + i ]["high"].min()
			dataframe.loc[ idx, "support" ] = float(support/3)

			resistance = 0
			last_cycles = [ 0, -1, -3 ] if not candle["trend"] else [ 0, -2, -4 ]
			for i in last_cycles:
				resistance += dataframe[ dataframe["cycle"] == candle["cycle"] + i ]["low"].max()
			dataframe.loc[ idx, "resistance" ] = float(resistance/3)

		# MOON INDICATORS
		#moon = pylunar.MoonInfo((28,2,4.9),(86,55,0.9))
		#def time_to_full_moon(moon, date):
		#	moon.update(date)
		#	return moon.time_to_full_moon() * 24
		#dataframe["time_to_full_moon"] = dataframe["date"].apply( lambda x: time_to_full_moon(moon, x) )
		#def time_to_new_moon(moon, date):
		#	moon.update(date)
		#	return moon.time_to_new_moon()
		#dataframe["time_to_new_moon"] = dataframe["date"].apply( lambda x: time_to_new_moon(moon, x) )

		# MOON PERIODS
		#def period(moon, date):
		#	moon.update(date)
		#	nm_sec = moon.time_to_new_moon()*60*60
		#	if nm_sec - 1031220 <= 0 and nm_sec - 564020 > 0:
		#		# green
		#		return 1.12
		#	if nm_sec - 564020 <= 0 and nm_sec - 298620 > 0:
		#		# black
		#		return 0.78
		#	if nm_sec - 298620 <= 0 and nm_sec - 298620 + 612000 > 0:
		#		# green
		#		return 1.12
		#	if nm_sec - 1819620 <= 0 and nm_sec - 1531920 >= 0:
		#		# yellow
		#		return 1.22
		#	# red is remainder
		#	return 0.93
		#dataframe["moon_period"] = dataframe["date"].apply( lambda x: period(moon, x) )

		#dataframe["res2sup"] = ( dataframe["resistance"] / dataframe["support"] ) * dataframe["moon_period"]

		# todo: idea is a dynamic stoploss. probably not possible
		#moon.update(datetime.datetime.now())
		#black_start = 574020
		#black_end = 298620
		#nm_sec = moon.time_to_new_moon()*60*60
		#self.stoploss = self.STOPLOSS_DEFAULT
		#if nm_sec - black_start >= 0 and nm_sec - black_end >= 0:
		#	self.stoploss = self.stoploss / 2
		#print(moon.time_to_new_moon())
		#print(nm_sec)


		#pandas.set_option("display.max_rows", 200)
		#print(dataframe)
		#import code
		#code.interact(local=locals())
		#input()

		return dataframe

	def populate_buy_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		buy = (
			(dataframe["tacitus"] < 0.40) &
			(dataframe["srsi_k"] < dataframe["srsi_d"]) &
			(dataframe["short"] < dataframe["long"])
		)
		dataframe.loc[ buy, "buy" ] = 1
		return dataframe

	def populate_sell_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		sell = (
			(dataframe["tacitus"] > 0.90) &
			((dataframe["srsi_k"] > dataframe["srsi_d"]) | (dataframe["srsi_k"] > 0.9)) &
			(dataframe["srsi_k"] > 50) &
			(dataframe["short"] > dataframe["long"])
		)
		dataframe.loc[ sell, "sell" ] = 1
		return dataframe

