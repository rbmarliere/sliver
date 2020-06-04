import freqtrade
import numpy
import pandas
import talib

class hypnox(freqtrade.strategy.interface.IStrategy):
	INTERFACE_VERSION = 2
	ticker_interval = "4h"
	minimal_roi = { "0": 100 } # disabled
	stoploss = -100 # disabled

	def populate_indicators(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		dataframe["ema9"] = talib.abstract.EMA(dataframe, timeperiod=9)
		dataframe["ema55"] = talib.abstract.EMA(dataframe, timeperiod=55)

		dataframe["cross_bear"] = freqtrade.vendor.qtpylib.indicators.crossed_below(dataframe["ema9"], dataframe["ema55"])
		dataframe["cross_bull"] = freqtrade.vendor.qtpylib.indicators.crossed_above(dataframe["ema9"], dataframe["ema55"])

		cycles = dataframe[ ( dataframe["cross_bull"] == True ) | ( dataframe["cross_bear"] == True ) ]
		print(cycles.tail(6))
		bear_sum = bull_sum = 0
		i = 2
		while i < 7:
			idx_cycle = cycles.tail(i).head(2)
			i += 1
			begin = idx_cycle.iloc[0]["date"]
			end = idx_cycle.iloc[1]["date"]
			cycle = dataframe.loc[ ( dataframe["date"] >= begin ) & ( dataframe["date"] <= end ) ]
			print(cycle.iloc[0]["date"])
			if cycle.iloc[0]["cross_bull"]:
				bull_sum += cycle["low"].max()
				print("BULL low:" + str(cycle["high"].max()))
			else:
				bear_sum += cycle["high"].min()
				print("BEAR high: " + str(cycle["low"].min()))

		current_cycle = dataframe[ ( dataframe["date"] >= cycles.iloc[-1]["date"] ) ]
		if current_cycle.iloc[0]["cross_bull"]:
			bull_sum += current_cycle["high"].max()
			print("BULL HIGH:" + str(current_cycle["high"].max()))
		else:
			bear_sum += current_cycle["low"].min()
			print("BEAR LOW: " + str(current_cycle["high"].max()))

		resistance = bull_sum / 3
		support = bear_sum / 3

		return dataframe

	def populate_buy_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		return dataframe

	def populate_sell_trend(self, dataframe: pandas.DataFrame, metadata: dict) -> pandas.DataFrame:
		return dataframe

