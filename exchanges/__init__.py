import enum

from .ccxt import CCXT
# from .mt5 import MT5
# from .uniswap import UNISWAP


class Types(enum.IntEnum):
    CCXT = 0
    MT5 = 1
    UNISWAP = 2


def load(exchange, **kwargs):
    if exchange.type == Types.CCXT:
        return CCXT(exchange, **kwargs)

    # elif exchange.type == Types.MT5:
    #     return MT5(exchange, **kwargs)

    # elif exchange.type == Types.UNISWAP:
    #     return UNISWAP(exchange, **kwargs)
