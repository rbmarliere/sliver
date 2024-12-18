import datetime
import random
import time
from logging import info

import ccxt
import pandas

from sliver.asset import Asset
from sliver.balance import Balance
from sliver.config import Config
from sliver.exceptions import AuthenticationError, DisablingError, PostponingError
from sliver.exchange import Exchange
from sliver.exchange_asset import ExchangeAsset
from sliver.order import Order


class CCXT(Exchange):
    @Exchange.api.setter
    def api(self, credential=None):
        api_key = {}

        if credential:
            api_key = {
                "apiKey": credential.api_key,
                "secret": credential.api_secret,
                "password": credential.api_password,
            }

        ccxt_class = getattr(ccxt, self.name)
        self._api = ccxt_class(api_key)

        try:
            sandbox_mode = Config().ENV_NAME == "development"
            self._api.set_sandbox_mode(sandbox_mode)
        except ccxt.NotSupported:
            raise DisablingError("sandbox mode not supported")

        self.check_latency()

    def api_call(call):
        def inner(self, *args, **kwargs):
            try:
                # TODO proper multiprocess rate limiting
                time.sleep(random.random() / 2)

                return call(self, *args, **kwargs)

            except ccxt.BadSymbol:
                pass

            except ccxt.RateLimitExceeded:
                sleep_time = 60
                if self.rate_limit:
                    sleep_time = self.rate_limit
                info(f"rate limited, sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)
                return inner(self, *args, **kwargs)

            except ccxt.RequestTimeout:
                info("ccxt request timed out")
                time.sleep(5)
                return inner(self, *args, **kwargs)

            except ccxt.AuthenticationError as e:
                raise AuthenticationError("ccxt authentication error", e)

            except ccxt.ExchangeError as e:
                raise DisablingError("ccxt error", e)

            except (ccxt.OnMaintenance, ccxt.NetworkError) as e:
                raise PostponingError("ccxt error", e)

        return inner

    @api_call
    def api_fetch_time(self):
        if self._api.has["fetchTime"]:
            return int(self._api.fetch_time() / 1000)

        return 0

    @api_call
    def api_fetch_balance(self):
        return self._api.fetch_balance()

    @api_call
    def api_fetch_ticker(self, symbol):
        return self._api.fetch_ticker(symbol)

    @api_call
    def api_fetch_last_price(self, symbol):
        return self.api_fetch_ticker(symbol)["last"]

    @api_call
    def api_fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
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
    def api_create_order(self, symbol, type, side, amount, price):
        try:
            if type == "market":
                new_order = self._api.create_order(symbol, type, side, amount)
            else:
                new_order = self._api.create_order(symbol, type, side, amount, price)

            return new_order["id"]

        except ccxt.InvalidOrder:
            info("invalid order parameters, skipping...")

        except ccxt.InsufficientFunds:
            raise DisablingError("insufficient funds")

        except ccxt.RequestTimeout:
            info("order creation request timeout")

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
                    info("order was created and is open")
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
                    info("order was created and is closed")
                    return last_order["id"]

    @api_call
    def get_synced_order(self, position, oid) -> Order:
        market = position.user_strategy.strategy.market

        order = Order.get_or_none(exchange_order_id=oid)
        if order is None or order.position_id != position.id:
            order = Order()

        ex_order = self.api_fetch_orders(market.get_symbol(), oid=oid)

        order.position = position
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
        order.price = market.quote.transform(price)
        order.amount = market.base.transform(amount)
        order.cost = market.quote.transform(cost)
        order.filled = market.base.transform(filled)

        if order.id or order.type == "market":
            info(f"syncing {order.side} order {oid}")
            info(f"filled: {market.base.print(order.filled)}")
            implicit_cost = market.base.format(order.amount) * order.price
            if implicit_cost > 0:
                info(
                    f"{market.base.print(order.amount)} @ "
                    f"{market.quote.print(order.price)} "
                    f"({market.quote.print(implicit_cost)})"
                )

        # check for fees
        if ex_order["fee"] is None:
            # TODO maybe fetch from difference between insertion & filled
            order.fee = 0
        else:
            try:
                order.fee = market.quote.transform(ex_order["fee"]["cost"])
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

    def sync_user_balance(self, user):
        info(f"syncing user balance in exchange {self.name}")

        ex_bal = self.api_fetch_balance()

        for ticker in ex_bal["total"]:
            total = ex_bal["total"][ticker]

            asset, new = Asset.get_or_create(ticker=ticker.upper())
            if new:
                info(f"saved new asset {asset.ticker}")

            ex_asset, new = ExchangeAsset.get_or_create(exchange=self, asset=asset)
            if new:
                info(f"saved asset {ex_asset.asset.ticker}")

            u_bal, new = Balance.get_or_create(user=user, asset=ex_asset)
            if new:
                info(f"saved new balance {u_bal.id}")

            u_bal.total = ex_asset.transform(total)
            u_bal.save()
