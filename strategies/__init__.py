import enum

from .hypnox import HypnoxStrategy
from .manual import ManualStrategy
from .random import RandomStrategy


class Types(enum.Enum):
    MANUAL = 0
    RANDOM = 1
    HYPNOX = 2


def load(strategy):
    if strategy.type == Types.MANUAL.value:
        return ManualStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.RANDOM.value:
        return RandomStrategy.get_or_create(strategy=strategy)[0]

    elif strategy.type == Types.HYPNOX.value:
        return HypnoxStrategy.get_or_create(strategy=strategy)[0]

    else:
        raise ValueError("invalid strategy type")
