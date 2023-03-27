import datetime
import time

import ccxt
import pandas

from sliver.config import Config
from sliver.exceptions import DisablingError, PostponingError
from sliver.exchange import Exchange
from sliver.order import Order
from sliver.print import print


class CCXT(Exchange):
    @Exchange.api.setter
    def api(self, credential=None):
        api_key = {}

        if credential:
            api_key = {"apiKey": credential.api_key, "secret": credential.api_secret}

        ccxt_class = getattr(ccxt, self.name)
        self._api = ccxt_class(api_key)

        try:
            sandbox_mode = Config().ENV_NAME == "development"
            self._api.set_sandbox_mode(sandbox_mode)
        except AttributeError:
            raise DisablingError("sandbox mode not supported")

        self.check_latency()

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

                print("rate limited, sleeping for {s} seconds".format(s=sleep_time))
                time.sleep(sleep_time)

                return inner(self, *args, **kwargs)

            except ccxt.RequestTimeout as e:
                print("request timed out", exception=e)
                time.sleep(5)
                return inner(self, *args, **kwargs)

            except (ccxt.AuthenticationError, ccxt.ExchangeError) as e:
                raise DisablingError("ccxt error", e)

            except (ccxt.OnMaintenance, ccxt.NetworkError) as e:
                raise PostponingError("ccxt error", e)

        return inner

    @api_call
    def api_fetch_time(self):
        try:
            getattr(self._api, "fetch_time")
            return self._api.fetch_time()
        except AttributeError:
            return self._api.fetch_ticker("BTC/USDT")

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
    def api_fetch_ohlcv(self, symbol, timeframe, since=None, limit=500, page_size=500):
        if since:
            since = int(since.timestamp() * 1000)

        ohlcv = self._api.fetch_ohlcv(
            symbol, timeframe=timeframe, since=since, limit=limit
        )

        if not ohlcv:
            return pandas.DataFrame()

        df = pandas.DataFrame.from_records(ohlcv)
        df.columns = ["time", "open", "high", "low", "close", "volume"]
        df.time = pandas.to_datetime(df.time, origin="unix", unit="ms").dt.tz_localize(
            None
        )

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
    def api_create_order(self, symbol, type, side, amount, price=None):
        try:
            new_order = self._api.create_order(symbol, type, side, amount, price)

            return new_order["id"]

        except ccxt.InvalidOrder:
            print("invalid order parameters, skipping...")

        except ccxt.InsufficientFunds:
            raise DisablingError("insufficient funds")

        except ccxt.RequestTimeout as e:
            print("order creation request timeout", exception=e)

            time.sleep(10)

            open_orders = self.api_fetch_orders(symbol, status="open")
            if open_orders:
                last_order = open_orders[-1]
                last_cost = int(last_order["price"] * last_order["amount"])
                cost = int(price * amount)
                trade_dt = datetime.datetime.strptime(
                    last_order["datetime"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                # check if trade was made within 2min
                if (
                    trade_dt
                    > (datetime.datetime.utcnow() - datetime.timedelta(minutes=2))
                    and cost > last_cost * 0.999
                    and cost < last_cost * 1.001
                    and int(price) == int(last_order["price"])
                ):
                    print("order was created and is open")
                    return last_order["id"]

            closed_orders = self.api_fetch_orders(symbol, status="closed")
            if closed_orders:
                last_order = closed_orders[-1]
                last_cost = int(last_order["price"] * last_order["amount"])
                cost = int(price * amount)
                trade_dt = datetime.datetime.strptime(
                    last_order["datetime"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                # check if trade was made within 2min
                if (
                    trade_dt
                    > (datetime.datetime.utcnow() - datetime.timedelta(minutes=2))
                    and cost > last_cost * 0.999
                    and cost < last_cost * 1.001
                    and int(price) == int(last_order["price"])
                ):
                    print("order was created and is closed")
                    return last_order["id"]

    @api_call
    def get_synced_order(self, oid) -> Order:
        order = Order.get_or_none(exchange_order_id=oid)
        if order is None or order.position_id != self.position.id:
            order = Order()

        ex_order = self.api_fetch_orders(self.market.get_symbol(), oid=oid)

        order.position = self.position
        order.exchange_order_id = ex_order["id"]
        order.status = ex_order["status"]
        order.type = ex_order["type"]
        order.side = ex_order["side"]
        order.time = ex_order["datetime"]
        if not ex_order["datetime"]:
            order.time = datetime.datetime.utcnow()

        price = ex_order["average"]
        amount = ex_order["amount"]
        filled = ex_order["filled"]
        if not filled:
            filled = 0
        cost = ex_order["cost"]
        if not cost:
            cost = filled * amount

        # transform values to db entry standard
        order.price = self.market.quote.transform(price)
        order.amount = self.market.base.transform(amount)
        order.cost = self.market.quote.transform(cost)
        order.filled = self.market.base.transform(filled)

        if order.id:
            print("syncing {s} order {i}".format(s=order.side, i=oid))
            print("filled: {f}".format(f=self.market.base.print(filled)))
            implicit_cost = self.market.base.format(amount) * order.price
            if implicit_cost > 0:
                print(
                    "{a} @ {p} ({c})".format(
                        a=self.market.base.print(amount),
                        p=self.market.quote.print(price),
                        c=self.market.quote.print(implicit_cost),
                    )
                )

        # check for fees
        if ex_order["fee"] is None:
            # TODO maybe fetch from difference between insertion & filled
            order.fee = 0
        else:
            try:
                order.fee = self.market.quote.transform(ex_order["fee"]["cost"])
            except KeyError:
                order.fee = 0

        if not order.status:
            if self.id:
                if filled == cost:
                    order.status = "closed"
                else:
                    order.status = "canceled"
            else:
                order.status = "open"

        order.save()

        return order
