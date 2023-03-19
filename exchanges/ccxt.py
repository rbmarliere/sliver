import datetime
import time

import pandas

import ccxt
import core
from .base import BaseExchange
from core.watchdog import info as i


class CCXT(BaseExchange):
    def api_call(call):
        def inner(self, *args, **kwargs):
            try:
                return call(self, *args, **kwargs)

            except ccxt.BadSymbol:
                pass

            except ccxt.RateLimitExceeded:
                sleep_time = 60
                if self.market:
                    sleep_time = self.market.base.exchange.rate_limit

                i("rate limited, sleeping for {s} seconds"
                  .format(s=sleep_time))
                time.sleep(sleep_time)

                return inner(self, *args, **kwargs)

            except ccxt.RequestTimeout as e:
                core.watchdog.error("request timed out", e)
                time.sleep(5)
                return inner(self, *args, **kwargs)

            except ccxt.AuthenticationError as e:
                raise core.errors.DisablingError("authentication error", e)

            except ccxt.OnMaintenance as e:
                raise core.errors.PostponingError("exchange on maintenance", e)

            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                raise core.errors.DisablingError("ccxt error", e)

        return inner

    @BaseExchange.api.setter
    def api(self, credential=None):
        api_key = {}

        if credential:
            api_key = {"apiKey": credential.api_key,
                       "secret": credential.api_secret}

        ccxt_class = getattr(ccxt, self.exchange.name)
        self._api = ccxt_class(api_key)

        try:
            sandbox_mode = core.config["ENV_NAME"] == "development"
            self._api.set_sandbox_mode(sandbox_mode)
        except AttributeError:
            raise core.errors.DisablingError("sandbox mode not supported")

        try:
            getattr(self._api, "fetch_time")
        except AttributeError:
            return

        started = datetime.datetime.utcnow()
        self.api_fetch_time()
        elapsed = datetime.datetime.utcnow() - started
        elapsed_in_ms = int(elapsed.total_seconds() * 1000)
        # i("api latency is {l} ms".format(l=elapsed_in_ms))

        if elapsed_in_ms > 5000:
            msg = "latency above threshold: {l} > 5000".format(l=elapsed_in_ms)
            raise core.errors.PostponingError(msg)

    @api_call
    def api_fetch_time(self):
        return self._api.fetch_time()

    @api_call
    def api_fetch_balance(self):
        return self._api.fetch_balance()

    @api_call
    def api_fetch_markets(self, symbol=None):
        return self._api.fetch_markets()

    @api_call
    def api_fetch_ticker(self, symbol):
        return self._api.fetch_ticker(symbol)

    @api_call
    def api_fetch_last_price(self, symbol):
        return self._api.fetch_ticker(symbol)["last"]

    @api_call
    def api_fetch_ohlcv(self,
                        symbol,
                        timeframe,
                        since=None,
                        limit=500,
                        page_size=500):
        if since:
            since = int(since.timestamp() * 1000)

        ohlcv = self._api.fetch_ohlcv(symbol,
                                      timeframe=timeframe,
                                      since=since,
                                      limit=limit)

        df = pandas.DataFrame.from_records(ohlcv)
        df.columns = ["time", "open", "high", "low", "close", "volume"]
        df.time = pandas.to_datetime(df.time, origin="unix", unit="ms") \
            .dt.tz_localize(None)

        return df

    @api_call
    def api_fetch_orders(self, symbol, oid=None, status=None):
        if oid is not None:
            return self._api.fetch_order(oid, symbol)

        if status == "open":
            return self._api.fetch_open_orders(symbol)
        elif status == "closed":
            return self._api.fetch_closed_orders(symbol)

        return self._api.fetch_orders(symbol)

    @api_call
    def api_cancel_orders(self, symbol, oid=None):
        try:
            if oid is None:
                self._api.cancel_all_orders(symbol)
                return True

            self._api.cancel_order(oid, symbol)
            return True

        except ccxt.OrderNotFound:
            # order.status = 'missing' ?
            return False

    @api_call
    def api_create_order(self, type, side, amount, price=None):
        try:
            new_order = self._api.create_order(self.market.get_symbol(),
                                               type,
                                               side,
                                               amount,
                                               price)

            return new_order["id"]

        except ccxt.InvalidOrder:
            i("invalid order parameters, skipping...")

        except ccxt.InsufficientFunds:
            core.watchdog.error("insufficient funds")
            self.position.user_strategy.disable()

        except ccxt.RequestTimeout as e:
            core.watchdog.error("order creation request timeout", e)

            time.sleep(10)

            open_orders = self.api_cancel_orders(self.market.get_symbol(),
                                                 status="open")
            if open_orders:
                last_order = open_orders[-1]
                last_cost = int(last_order["price"] * last_order["amount"])
                cost = int(price * amount)
                trade_dt = datetime.datetime.strptime(last_order["datetime"],
                                                      "%Y-%m-%dT%H:%M:%S.%fZ")
                # check if trade was made within 2min
                if trade_dt > (datetime.datetime.utcnow()
                               - datetime.timedelta(minutes=2)) \
                        and cost > last_cost*0.999 and cost < last_cost*1.001 \
                        and int(price) == int(last_order["price"]):
                    i("order was created and is open")
                    return last_order["id"]

            closed_orders = self.api_fetch_orders(self.market.get_symbol(),
                                                  status="closed")
            if closed_orders:
                last_order = closed_orders[-1]
                last_cost = int(last_order["price"] * last_order["amount"])
                cost = int(price * amount)
                trade_dt = datetime.datetime.strptime(last_order["datetime"],
                                                      "%Y-%m-%dT%H:%M:%S.%fZ")
                # check if trade was made within 2min
                if trade_dt > (datetime.datetime.utcnow()
                               - datetime.timedelta(minutes=2)) \
                        and cost > last_cost*0.999 and cost < last_cost*1.001 \
                        and int(price) == int(last_order["price"]):
                    i("order was created and is closed")
                    return last_order["id"]
