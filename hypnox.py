import freqtrade
import numpy
import pandas
import talib
import pylunar

class hypnox(freqtrade.strategy.interface.IStrategy):
	INTERFACE_VERSION = 2
	ticker_interval = "4h"
	minimal_roi = { "0": 100 } # disabled
	stoploss = -100 # disabled
	resistance = 0
	support = 0
	trend = 0 # 0 bear 1 bull

	def populate_indicators(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		ema9 = talib.abstract.EMA(dataframe, timeperiod=9)
		ema55 = talib.abstract.EMA(dataframe, timeperiod=55)

		bear_crosses = freqtrade.vendor.qtpylib.indicators.crossed_below(ema9, ema55)
		bull_crosses = freqtrade.vendor.qtpylib.indicators.crossed_above(ema9, ema55)

		crosses = dataframe[ ( bear_crosses == True ) | ( bull_crosses == True ) ]
		last_cross = crosses.iloc[-1]["date"]
		last_bullcross = dataframe[ ( bull_crosses == True ) ].iloc[-1]["date"]
		self.trend = last_cross == last_bullcross

		bear_sum = bull_sum = 0
		current_cycle = dataframe[ dataframe["date"] >= last_cross ]
		if self.trend:
			bull_sum = current_cycle["low"].max()
		else:
			bear_sum = current_cycle["high"].max()

		i = 2
		t = self.trend
		while i < 7:
			idx_cycle = crosses.tail(i).head(2)
			begin = idx_cycle.iloc[0]["date"]
			end = idx_cycle.iloc[1]["date"]
			cycle = dataframe.loc[ ( dataframe["date"] >= begin ) & ( dataframe["date"] <= end ) ]
			if t:
				bear_sum += cycle["high"].min()
			else:
				bull_sum += cycle["low"].max()
			t = not t
			i += 1

		self.resistance = int(bull_sum / 3)
		self.support = int(bear_sum / 3)

		moon = pylunar.MoonInfo((57,15,55),(4,28,28))
		def time_to_full_moon(moon, date):
			moon.update(date)
			return moon.time_to_full_moon()
		dataframe.loc[:, "time_to_full_moon"] = 0
		dataframe["time_to_full_moon"] = dataframe["date"].apply(lambda x: time_to_full_moon(moon, x))

		return dataframe

	def populate_buy_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		dataframe.loc[ :,
			"buy" ] = 1
		#print(dataframe.tail())
		return dataframe

	def populate_sell_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		dataframe.loc[ :,
			"sell" ] = 1
		#print(dataframe.tail())
		return dataframe

