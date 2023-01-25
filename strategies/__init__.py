import enum

import core
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
        mixins = []
        for st in strategy.mixins:
            mixins.append(
                {"strategy": load(core.db.Strategy.get_by_id(st.strategy_id)),
                 "weight": st.weight})
        stt.mixins = mixins

    else:
        raise ValueError("invalid strategy type")

    if user is not None:
        stt.load_fields(user)

    return stt
