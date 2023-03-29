from sliver.exceptions import DisablingError
from sliver.strategies.bb import BBStrategy as BB
from sliver.strategies.dd3 import DD3Strategy as DD3
from sliver.strategies.hypnox import HypnoxStrategy as Hypnox
from sliver.strategies.ma_cross import MACrossStrategy as MACross
from sliver.strategies.manual import ManualStrategy as Manual
from sliver.strategies.mixer import MixerStrategy as Mixer
from sliver.strategies.random import RandomStrategy as Random
from sliver.strategies.swapperbox import SwapperBoxStrategy as SwapperBox
from sliver.strategies.types import StrategyTypes


class StrategyFactory:
    @classmethod
    def from_base(cls, strategy):
        if strategy.type == StrategyTypes.BB:
            return BB.get_or_create(strategy=strategy)[0]

        elif strategy.type == StrategyTypes.DD3:
            return DD3.get_or_create(strategy=strategy)[0]

        elif strategy.type == StrategyTypes.HYPNOX:
            return Hypnox.get_or_create(strategy=strategy)[0]

        elif strategy.type == StrategyTypes.MA_CROSS:
            return MACross.get_or_create(strategy=strategy)[0]

        elif strategy.type == StrategyTypes.MANUAL:
            return Manual.get_or_create(strategy=strategy)[0]

        elif strategy.type == StrategyTypes.MIXER:
            return Mixer.get_or_create(strategy=strategy)[0]

        elif strategy.type == StrategyTypes.RANDOM:
            return Random.get_or_create(strategy=strategy)[0]

        elif strategy.type == StrategyTypes.SWAPPERBOX:
            return SwapperBox.get_or_create(strategy=strategy)[0]

        else:
            raise DisablingError("invalid strategy type")
