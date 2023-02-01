import enum

from .bb import BBStrategy
from .dd3 import DD3Strategy
from .hypnox import HypnoxStrategy
from .manual import ManualStrategy
from .mixer import MixerStrategy
from .random import RandomStrategy


class Types(enum.Enum):
    MANUAL = 0
    RANDOM = 1
    HYPNOX = 2
    DD3 = 3
    MIXER = 4
    BB = 5


class Signal(enum.Enum):
    SELL = -1
    NEUTRAL = 0
    BUY = 1


def load(strategy, user=None):
    if strategy.type == Types.MANUAL.value:
        stt = ManualStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.RANDOM.value:
        stt = RandomStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.HYPNOX.value:
        stt = HypnoxStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.DD3.value:
        stt = DD3Strategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.MIXER.value:
        stt = MixerStrategy.get_or_create(strategy=strategy)[0]
        stt.strategies = [m.strategy_id for m in strategy.mixins]
        stt.weights = [m.weight for m in strategy.mixins]

    elif strategy.type == Types.BB.value:
        stt = BBStrategy.get_or_create(strategy=strategy)[0]

    else:
        raise ValueError("invalid strategy type")

    if user is not None:
        stt.load_fields(user)

    return stt
