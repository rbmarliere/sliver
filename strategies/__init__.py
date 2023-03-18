import enum

from .bb import BBStrategy
from .dd3 import DD3Strategy
from .hypnox import HypnoxStrategy
from .ma_cross import MACrossStrategy
from .manual import ManualStrategy
from .mixer import MixerStrategy
from .random import RandomStrategy
from .swapperbox import SwapperBoxStrategy


class Types(enum.IntEnum):
    MANUAL = 0
    RANDOM = 1
    HYPNOX = 2
    DD3 = 3
    MIXER = 4
    BB = 5
    MA_CROSS = 6
    SWAPPERBOX = 7


class Signal(enum.IntEnum):
    SELL = -1
    NEUTRAL = 0
    BUY = 1


def load(strategy, user=None):
    if strategy.type == Types.MANUAL:
        stt = ManualStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.RANDOM:
        stt = RandomStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.HYPNOX:
        stt = HypnoxStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.DD3:
        stt = DD3Strategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.MIXER:
        stt = MixerStrategy.get_or_create(strategy=strategy)[0]
        stt.strategies = [m.strategy_id for m in strategy.mixins]
        stt.buy_weights = [m.buy_weight for m in strategy.mixins]
        stt.sell_weights = [m.sell_weight for m in strategy.mixins]

    elif strategy.type == Types.BB:
        stt = BBStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.MA_CROSS:
        stt = MACrossStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.SWAPPERBOX:
        stt = SwapperBoxStrategy.get_or_create(strategy=strategy)[0]

    else:
        raise ValueError("invalid strategy type")

    if user is not None:
        stt.load_fields(user)

    return stt
