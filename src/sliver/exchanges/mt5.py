import socket

import rpyc

from sliver.config import Config
from sliver.exceptions import DisablingError
from sliver.exchange import Exchange


class MT5(Exchange):
    @Exchange.api.setter
    def api(self, credential=None):
        try:
            conn = rpyc.classic.connect("localhost")
        except socket.error:
            raise DisablingError("mt5 rpyc server not running")

        try:
            self._api = conn.modules.MetaTrader5
        except AttributeError:
            raise DisablingError("mt5 python api not installed")

        try:
            assert credential.api_key
            assert credential.api_secret
            assert credential.exchange.api_endpoint
            if Config().ENV_NAME == "development":
                assert credential.exchange.api_sandbox_endpoint
        except (AttributeError, AssertionError) as e:
            raise DisablingError("mt5 cred or api not set", e)

        term = self._api.initialize(
            login=int(credential.api_key),
            password=credential.api_secret,
            server=credential.exchange.api_endpoint,
        )

        if not term:
            raise DisablingError(
                "mt5 terminal not initialized: {e}".format(e=self._api.last_error())
            )

        if self._api.terminal_info() is None:
            raise DisablingError("mt5 terminal not running")

        if not self._api.symbol_select("PETR4", True):
            raise DisablingError(
                "mt5 failed to select: {e}".format(e=self._api.last_error())
            )

        self.check_latency()

    def api_call(call):
        def inner(self, *args, **kwargs):
            ret = call(self, *args, **kwargs)

            if not ret:
                e = self._api.last_error()[1]
                raise DisablingError("mt5 error: {e}".format(e=e))

            return ret

        return inner

    @api_call
    def api_fetch_time(self):
        return self._api.symbol_info_tick("PETR4")

    @api_call
    def api_fetch_balance(self):
        # there is also positions_total
        return self._api.account_info().equity  # in BRL

    @api_call
    def api_fetch_markets(self):
        ...

    @api_call
    def api_fetch_ticker(self, symbol):
        info = self._api.symbol_info(symbol)
        if not info:
            return

        if not info.visible:
            if not self._api.symbol_select(symbol, True):
                return

        return self._api.symbol_info_tick(symbol)

    @api_call
    def api_fetch_ohlcv(
        self, symbol, timeframe, since=None, limit=None, page_size=None
    ):
        # returns pandas dataframe
        ...

    @api_call
    def api_fetch_orders(self, symbol, oid=None, status=None):
        # single, all, or based on status (open, closed, canceled)
        ...

    @api_call
    def api_cancel_orders(self, symbol, oid=None):
        # if oid is none, cancel all orders
        if oid:
            request = {"order": oid, "action": self._api.TRADE_ACTION_REMOVE}
            ret = self._api.order_send(request)
            if ret.retcode == self._api.TRADE_RETCODE_DONE:
                return ret.order
        else:
            orders = self._api.orders_get()
            for o in orders:
                request = {"order": o.ticket, "action": self._api.TRADE_ACTION_REMOVE}
                self._api.order_send(request)
            # return ?

    @api_call
    def api_create_order(self, symbol, type, side, amount, price=None):
        last = self.api_fetch_ticker(symbol)

        if type == "market":
            type = self._api.TRADE_ACTION_DEAL
        else:
            type = self._api.TRADE_ACTION_PENDING

        if side == "buy":
            side = self._api.ORDER_TYPE_BUY
            if price is None:
                price = last.ask
        else:
            side = self._api.ORDER_TYPE_SELL
            if price is None:
                price = last.bid

        request = {
            "action": type,
            "symbol": symbol,
            "volume": float(amount),
            "type": type,
            "price": price,
            "sl": 0.0,
            "tp": 0.0,
            "deviation": 0.0,
            "magic": 0,
            "comment": "sliver",
            "type_time": self._api.ORDER_TIME_GTC,
            "type_filling": self._api.ORDER_FILLING_RETURN,
        }

        ret = self._api.order_send(request)
        if ret.retcode == self._api.TRADE_RETCODE_DONE:
            return ret.order
