from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import numpy as np
import pandas as pd

from freqtrade.data.history import load_pair_history
from sklearn.preprocessing import MinMaxScaler
import freqtrade.vendor.qtpylib.indicators as qtpylib
import keras
import talib.abstract as ta

class Hypnox(IStrategy):
	scaler = MinMaxScaler(feature_range=(0, 1))
	INTERFACE_VERSION = 2
	minimal_roi = {
		"60": 0.01,
		"30": 0.02,
		"0": 0.04
	}
	stoploss = -0.10
	trailing_stop = False
	# trailing_only_offset_is_reached = False
	# trailing_stop_positive = 0.01
	# trailing_stop_positive_offset = 0.0
	ticker_interval = '4h'
	process_only_new_candles = False
	use_sell_signal = True
	sell_profit_only = False
	ignore_roi_if_buy_signal = False
	startup_candle_count: int = 20
	order_types = {
		'buy': 'limit',
		'sell': 'limit',
		'stoploss': 'market',
		'stoploss_on_exchange': False
	}
	order_time_in_force = {
		'buy': 'gtc',
		'sell': 'gtc'
	}
	plot_config = {
		'main_plot': {
			'tema': {},
			'sar': {'color': 'white'},
		},
		'subplots': {
			"MACD": {
				'macd': {'color': 'blue'},
				'macdsignal': {'color': 'orange'},
			},
			"RSI": {
				'rsi': {'color': 'red'},
			}
		}
	}

	def informative_pairs(self):
		return []

	def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
		df = load_pair_history(pair=metadata['pair'],
			timeframe=self.config['ticker_interval'],
			datadir=self.config['datadir']
		)
		print(df.tail())
		return dataframe

	def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
		#mfile = open('model.json', 'r')
		#mjson = mfile.read()
		#mfile.close()
		#model = keras.models.model_from_json(mjson)
		#model.load_weights('model.h5')
		return dataframe

	def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
		return dataframe

