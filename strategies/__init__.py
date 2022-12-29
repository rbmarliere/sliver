import enum

from .dd3 import DD3Strategy
from .hypnox import HypnoxStrategy
from .manual import ManualStrategy
from .random import RandomStrategy


class Types(enum.Enum):
    MANUAL = 0
    RANDOM = 1
    HYPNOX = 2
    DD3 = 3


def load(strategy, user=None):
    if strategy.type == Types.MANUAL.value:
        stt = ManualStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.RANDOM.value:
        stt = RandomStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.HYPNOX.value:
        stt = HypnoxStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.DD3.value:
        stt = DD3Strategy.get_or_create(strategy=strategy)[0]

    else:
        raise ValueError("invalid strategy type")

    if user is not None:
        stt.load_fields(user)

    return stt
