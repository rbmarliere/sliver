from sliver.exceptions import DisablingError
from sliver.exchanges.ccxt import CCXT
from sliver.exchanges.mt5 import MT5
from sliver.exchanges.types import ExchangeTypes


class ExchangeFactory:
    @classmethod
    def from_base(self, exchange):
        if exchange.type == ExchangeTypes.CCXT:
            exchange = CCXT.get(id=exchange.id)

        elif exchange.type == ExchangeTypes.MT5:
            exchange = MT5.get(id=exchange.id)

        else:
            raise DisablingError("invalid exchange type")

        exchange.api = None

        return exchange

    @classmethod
    def from_credential(self, credential):
        exchange = credential.exchange

        exchange = self.from_base(exchange)

        exchange.api = credential

        return exchange
