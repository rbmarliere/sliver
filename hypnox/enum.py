import enum


class Signal(enum.Enum):
    BUY = 'buy'
    NEUTRAL = 'neutral'
    SELL = 'sell'


class PositionStatus(enum.Enum):
    OPENING = 'opening'
    OPEN = 'open'
    CLOSED = 'closed'
    CLOSING = 'closing'


class OrderSide(enum.Enum):
    BUY = 'buy'
    SELL = 'sell'
