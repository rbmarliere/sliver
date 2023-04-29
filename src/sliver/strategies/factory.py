import enum

from sliver.exceptions import DisablingError
from sliver.strategies.bb import BBStrategy as BB
from sliver.strategies.dd3 import DD3Strategy as DD3
from sliver.strategies.hypnox import HypnoxStrategy as Hypnox
from sliver.strategies.ma_cross import MACrossStrategy as MACross
from sliver.strategies.manual import ManualStrategy as Manual
from sliver.strategies.mixer import MixerStrategy as Mixer
from sliver.strategies.random import RandomStrategy as Random
from sliver.strategies.swapperbox import SwapperBoxStrategy as SwapperBox
from sliver.strategies.windrunner import WindrunnerStrategy as Windrunner
from sliver.strategies.hypnoxv2 import Hypnoxv2Strategy as Hypnoxv2
from sliver.strategies.elnino import ElNinoStrategy as ElNino
from sliver.strategies.lanina import LaNinaStrategy as LaNina


class StrategyTypes(enum.IntEnum):
    MANUAL = 0
    RANDOM = 1
    HYPNOX = 2
    DD3 = 3
    MIXER = 4
    BB = 5
    MA_CROSS = 6
    SWAPPERBOX = 7
    WINDRUNNER = 8
    HYPNOXV2 = 9
    ELNINO = 10
    LANINA = 11


class StrategyFactory:
    @classmethod
    def from_base(cls, strategy):
        model = None

        if strategy.type == StrategyTypes.BB:
            model = BB
        elif strategy.type == StrategyTypes.DD3:
            model = DD3
        elif strategy.type == StrategyTypes.HYPNOX:
            model = Hypnox
        elif strategy.type == StrategyTypes.MA_CROSS:
            model = MACross
        elif strategy.type == StrategyTypes.MANUAL:
            model = Manual
        elif strategy.type == StrategyTypes.MIXER:
            model = Mixer
        elif strategy.type == StrategyTypes.RANDOM:
            model = Random
        elif strategy.type == StrategyTypes.SWAPPERBOX:
            model = SwapperBox
        elif strategy.type == StrategyTypes.WINDRUNNER:
            model = Windrunner
        elif strategy.type == StrategyTypes.HYPNOXV2:
            model = Hypnoxv2
        elif strategy.type == StrategyTypes.ELNINO:
            model = ElNino
        elif strategy.type == StrategyTypes.LANINA:
            model = LaNina

        if model is None:
            raise DisablingError("invalid strategy type")

        model.setup()

        return model.get_or_create(strategy=strategy)[0]
