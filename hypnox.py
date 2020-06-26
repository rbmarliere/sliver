import collections
import datetime
import freqtrade
import numpy
import os
import pandas
import pylunar
import talib.abstract as ta
import pytz


class hypnox(freqtrade.strategy.interface.IStrategy):
	INTERFACE_VERSION = 2
	STOPLOSS_DEFAULT = -0.03
	minimal_roi = { "0": 100 } # disabled
	stoploss = STOPLOSS_DEFAULT

	plot_config = {
		"main_plot": {
			"support": {},
			"resistance": {},
			"black": {}
		},
		"subplots": {
			#"res2sup": {
			#	"res2sup": {},
			#}
			"moon": {
			#	"time_to_full_moon": {},
				"moon_period": {}
			},
			#"srsi_k": {
			#	"srsi_k": {},
			#	"srsi_d": {},
			#}
		}
	}

	def populate_indicators(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		# TACITUS INDICATOR
		dataframe.insert(0, "tacitus", False)
		tally_dir = os.path.dirname(os.path.realpath(__file__)) + "/acheron/tally"
		groups = collections.defaultdict(list)
		for filename in os.listdir(tally_dir):
			basename, extension = os.path.splitext(filename)
			if extension != ".txt":
				continue
			tally_date = datetime.datetime.strptime(basename, "%Y%m%d-%H").replace(tzinfo=pytz.UTC)
			tally_result = open(tally_dir + "/" + filename).read().splitlines()[2].split()[1] == "True"
			dataframe.loc[ dataframe["date"] == tally_date, "tacitus" ] = tally_result

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

		dataframe["res2sup"] = 100 * ( dataframe["resistance"] - dataframe["support"] ) / dataframe["close"]

		# LUNATIC INDICATORS
		moon = pylunar.MoonInfo((28,2,4.9),(86,55,0.9))
		def time_to_full_moon(moon, date):
			moon.update(date)
			return moon.time_to_full_moon()
		dataframe["time_to_full_moon"] = dataframe["date"].apply( lambda x: time_to_full_moon(moon, x) )
		def time_to_new_moon(moon, date):
			moon.update(date)
			return moon.time_to_new_moon()
		dataframe["time_to_new_moon"] = dataframe["date"].apply( lambda x: time_to_new_moon(moon, x) )

		# LUNATIC PERIODS
		def period(moon, date):
			moon.update(date)
			nm_sec = moon.time_to_new_moon()*60*60
			if nm_sec - 1031220 <= 0 and nm_sec - 564020 > 0:
				# green
				return 1
			if nm_sec - 564020 <= 0 and nm_sec - 298620 > 0:
				# black
				return 2
			if nm_sec - 298620 <= 0 and nm_sec - 298620 + 612000 > 0:
				# green
				return 1
			if nm_sec - 1819620 <= 0 and nm_sec - 1531920 >= 0:
				# yellow
				return -1
			# red is remainder
			return 0
		dataframe["moon_period"] = dataframe["date"].apply( lambda x: period(moon, x) )

		#moon.update(datetime.datetime.now())
		#black_start = 574020
		#black_end = 298620
		#nm_sec = moon.time_to_new_moon()*60*60
		#self.stoploss = self.STOPLOSS_DEFAULT
		#if nm_sec - black_start >= 0 and nm_sec - black_end >= 0:
		#	self.stoploss = self.stoploss / 2
		#print(moon.time_to_new_moon())
		#print(nm_sec)

		# CLASSIC TECHNICAL INDICATORS
		#RSI
		dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
		#StochRSI
		period = 14
		smoothd = 3
		smoothk = 3
		stochrsi  = (dataframe["rsi"] - dataframe["rsi"].rolling(period).min()) / (dataframe["rsi"].rolling(period).max() - dataframe["rsi"].rolling(period).min())
		dataframe["srsi_k"] = stochrsi.rolling(smoothk).mean() * 100
		dataframe["srsi_d"] = dataframe["srsi_k"].rolling(smoothd).mean()
		#EMAs
		dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
		dataframe["ema55"] = ta.EMA(dataframe, timeperiod=55)

		return dataframe

	def populate_buy_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		buy = (
			(dataframe["srsi_k"] < 22) &
			(dataframe["res2sup"] < 2) &
			(dataframe["close"] <= dataframe["support"]) &
			(dataframe["time_to_new_moon"] <= 15) &
			(dataframe["tacitus"] == True)
		)
		dataframe.loc[ buy, "buy" ] = 1
		return dataframe

	def populate_sell_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		sell = (
			(dataframe["srsi_k"] > 78) &
			(dataframe["res2sup"] > 3) &
			(dataframe["close"] >= dataframe["resistance"]) &
			(dataframe["time_to_full_moon"] <= 10) &
			(dataframe["tacitus"] == False)
		)
		dataframe.loc[ sell, "sell" ] = 1
		return dataframe

