import datetime
import decimal
import time

import ccxt
import pandas
import peewee

import core
from core.watchdog import info as i


def set_api(exchange: core.db.Exchange = None,
            cred: core.db.Credential = None):
    global credential

    if cred is None:
        api_key = {}
        credential = None
    else:
        if "credential" in globals() and credential == cred:
            return
        credential = cred
        api_key = {"apiKey": credential.api_key,
                   "secret": credential.api_secret}
        exchange = credential.exchange

    global api
    exchange = getattr(ccxt, exchange.name)
    api = exchange(api_key)
    api.set_sandbox_mode(core.config["ENV_NAME"] == "development")
    # api.verbose = True

    # check if api is alive
    check_latency()


def check_latency():
    started = datetime.datetime.utcnow()

    try:
        getattr(api, "fetch_time")
    except AttributeError:
        i("exchange does not have fetch_time")
        return

    api.fetch_time()

    elapsed = datetime.datetime.utcnow() - started
    elapsed_in_ms = int(elapsed.total_seconds() * 1000)

    # i("api latency is {l} ms".format(l=elapsed_in_ms))

    if elapsed_in_ms > 5000:
        core.watchdog.error("latency above threshold ({l} > 5000)"
                            .format(l=elapsed_in_ms), None)
        raise ccxt.NetworkError


def download_prices(strategy: core.db.Strategy):
    set_api(exchange=strategy.market.base.exchange)

    now = datetime.datetime.utcnow()
    timeframe = strategy.timeframe
    market = strategy.market

    # check if symbol is supported by exchange
    symbols = [pair["symbol"] for pair in api.fetch_markets()]
    if market.get_symbol() not in symbols:
        core.watchdog.error("symbol not supported by exchange", None)
        raise ccxt.ExchangeError

    # check if timeframe is supported by exchange
    if timeframe not in api.timeframes:
        core.watchdog.error("timeframe not supported by exchange", None)
        raise ccxt.ExchangeError

    timeframe_delta = core.utils.get_timeframe_delta(timeframe)
    page_size = 500

    # fetch first and last price entries from the db
    try:
        filter = ((core.db.Price.market == market) &
                  (core.db.Price.timeframe == timeframe))
        desc = core.db.Price.time.desc()
        last_entry = core.db.Price.select().where(filter).order_by(
            desc).get().time
        page_start = last_entry + timeframe_delta
    except peewee.DoesNotExist:
        last_entry = datetime.datetime.utcfromtimestamp(0)
        page_start = datetime.datetime(2000, 1, 1)
        i("no db entries found, downloading everything...")

    # return if last entry is last possible result
    if page_start + timeframe_delta > now:
        i("price data is up to date")
        return

    prices = pandas.DataFrame(columns=[0, 1, 2, 3, 4, 5, 6, 7])
    while True:
        try:
            # api call with relevant params
            i("downloading from {s}".format(s=page_start))
            page = api.fetch_ohlcv(market.get_symbol(),
                                   since=int(page_start.timestamp() * 1000),
                                   timeframe=timeframe,
                                   limit=page_size)

            # check if received any data
            if not page:
                break

            # logging received range
            page_first = datetime.datetime.utcfromtimestamp(page[0][0] / 1000)
            page_last = datetime.datetime.utcfromtimestamp(page[-1][0] / 1000)
            i("received range {f} to {l}".format(f=page_first, l=page_last))

            # concatenating existing pages with current page
            prices = pandas.concat(
                [prices, pandas.DataFrame.from_records(page)])

            # break if received page is less than max size
            # TODO this will break if page_size is different than allowed
            if len(page) < page_size:
                break

            # increment the counter
            page_start = page_last + timeframe_delta

        except ccxt.RateLimitExceeded:
            sleep_time = market.base.exchange.rate_limit
            i("rate limited, sleeping for {s} seconds".format(s=sleep_time))
            time.sleep(sleep_time)
            continue

    # transform data for the database
    prices[0] = prices[0].apply(
        lambda x: datetime.datetime.utcfromtimestamp(x / 1000))
    prices[[1, 2, 3, 4]] = prices[[1, 2, 3, 4]] \
        .applymap(lambda x: market.quote.transform(x))
    prices[5] = prices[5].apply(lambda x: market.base.transform(x))
    prices[6] = timeframe
    prices[7] = market.id

    prices = prices.rename(columns={
        0: "time",
        1: "open",
        2: "high",
        3: "low",
        4: "close",
        5: "volume",
        6: "timeframe",
        7: "market_id"})

    # remove dups to avoid db errors
    prices = prices.drop_duplicates()

    if not prices.empty:
        last = prices.iloc[-1]
        if last.time + timeframe_delta > now:
            prices.drop(last.name, inplace=True)

        core.db.Price.insert_many(prices.to_dict("records")).execute()


def sync_limit_orders(position: core.db.Position) -> core.db.Position:
    # set user credential api
    user = position.user_strategy.user
    exchange = position.user_strategy.strategy.market.base.exchange
    credential = user.get_active_credential(exchange).get()
    set_api(cred=credential)

    market = position.user_strategy.strategy.market
    symbol = market.get_symbol()

    # fetch internal open orders
    orders = position.get_open_orders()

    # if no orders found, exit
    if len(orders) == 0:
        i("no open orders found")
        return

    for order in orders:
        oid = order.exchange_order_id
        i("updating {s} order {i}".format(s=order.side, i=oid))

        ex_order = None

        # cancel order first
        while True:
            try:
                ex_order = api.cancel_order(oid, symbol)
                break
            except ccxt.OrderNotFound:
                # order.status = 'missing' ?
                break
            except ccxt.RequestTimeout as e:
                core.watchdog.error("order cancellation request timeout", e)
                # retry after 10 seconds
                time.sleep(10)

        while True:
            try:
                # fetch order to ensure its data is up to date
                ex_order = api.fetch_order(oid, symbol)
                break
            except ccxt.OrderNotFound:
                time.sleep(10)
            except ccxt.RequestTimeout as e:
                core.watchdog.error("order fetch request timeout", e)
                time.sleep(10)

        if ex_order:
            order.sync(ex_order, position)


def create_order(type: str,
                 side: str,
                 position: core.db.Position,
                 amount: int,
                 price: int):
    # set user credential api
    user = position.user_strategy.user
    exchange = position.user_strategy.strategy.market.base.exchange
    credential = user.get_active_credential(exchange).get()
    set_api(cred=credential)

    market = position.user_strategy.strategy.market
    symbol = market.get_symbol()

    i("inserting {t} {s} order :: {a} @ {p}"
      .format(t=type,
              s=side,
              a=market.base.print(amount),
              p=market.quote.print(price)))
    try:
        assert amount >= market.amount_min
        assert price >= market.price_min
        assert amount * price >= market.cost_min
    except AssertionError:
        i("order values are smaller than exchange minimum, skipping...")
        return False

    amount = market.base.format(amount)
    price = market.quote.format(price)

    inserted = False

    try:
        new_order = api.create_order(symbol, type, side, amount, price)
        inserted = True
        new_oid = new_order["id"]

    except ccxt.InvalidOrder:
        i("invalid order parameters, skipping...")
        return False

    except ccxt.AuthenticationError as e:
        core.watchdog.error("authentication error", e)
        if "credential" in globals():
            credential.disable()
        return False

    except ccxt.RequestTimeout as e:
        core.watchdog.error("order creation request timeout", e)

        time.sleep(10)

        open_orders = core.exchange.api.fetchOpenOrders(symbol)
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
                new_oid = last_order["id"]
                inserted = True

        if not inserted:
            closed_orders = core.exchange.api.fetchClosedOrders(symbol)
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
                    new_oid = last_order["id"]

    if inserted:
        i("inserted {t} {s} order {i}".format(t=type, s=side, i=new_oid))
        while True:
            try:
                ex_order = api.fetch_order(new_oid, symbol)
                core.db.Order.sync(core.db.Order(), ex_order, position)
                break
            except ccxt.BaseError as e:
                core.watchdog.error("order fetch: ccxt error", e)
                # retry after 10 seconds
                time.sleep(10)

    return True


def create_limit_buy_orders(total_cost: int,
                            position: core.db.Position,
                            last_price: int,
                            num_orders: int,
                            spread_pct: decimal.Decimal):

    # set user credential api
    user = position.user_strategy.user
    exchange = position.user_strategy.strategy.market.base.exchange
    credential = user.get_active_credential(exchange).get()
    set_api(cred=credential)

    market = position.user_strategy.strategy.market

    # compute price delta based on given spread
    delta = market.quote.div(last_price * spread_pct,
                             market.quote.transform(100),
                             prec=market.price_precision)

    init_price = last_price - delta

    # compute cost for each order given a number of orders to create
    unit_cost = market.quote.div(total_cost,
                                 market.quote.transform(num_orders),
                                 prec=market.price_precision)

    # compute prices for each order
    unit_spread = market.quote.div(delta,
                                   market.quote.transform(num_orders),
                                   prec=market.price_precision)
    spreads = [init_price] + [unit_spread] * num_orders
    prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

    i("unit cost is {c}".format(c=market.quote.print(unit_cost)))

    # send a single order if cost of each order is lower than market minimum
    if unit_cost < market.cost_min:
        i("unitary cost is less than exchange minimum, creating single order")

        # get average price for single order
        avg_price = market.quote.div(sum(prices),
                                     market.quote.transform(len(prices)),
                                     prec=market.price_precision)
        total_amount = market.base.div(total_cost,
                                       avg_price,
                                       prec=market.amount_precision)
        return create_order("limit", "buy", position, total_amount, avg_price)

    # avoid rounding errors
    cost_remainder = total_cost - sum([unit_cost] * num_orders)
    if cost_remainder != 0:
        i("bucket remainder: {r}".format(r=market.quote.print(cost_remainder)))

    # creates bucket orders if reached here, which normally it will
    for price in prices:
        amount = market.base.div(unit_cost,
                                 price,
                                 prec=market.amount_precision)

        if price == prices[-1]:
            amount += market.base.div(cost_remainder,
                                      price,
                                      prec=market.amount_precision)

        return create_order("limit", "buy", position, amount, price)


def create_limit_sell_orders(total_amount: int,
                             position: core.db.Position,
                             last_price: int,
                             num_orders: int,
                             spread_pct: decimal.Decimal):

    # set user credential api
    user = position.user_strategy.user
    exchange = position.user_strategy.strategy.market.base.exchange
    credential = user.get_active_credential(exchange).get()
    set_api(cred=credential)

    market = position.user_strategy.strategy.market

    # compute price delta based on given spread
    delta = market.quote.div(last_price * spread_pct,
                             market.quote.transform(100),
                             prec=market.price_precision)
    init_price = last_price + delta

    # compute prices for each order
    unit_spread = market.quote.div(-delta,
                                   market.quote.transform(num_orders),
                                   prec=market.price_precision)
    spreads = [init_price] + [unit_spread] * num_orders
    prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

    # compute amount for each order given a number of orders to create
    unit_amount = market.base.div(total_amount,
                                  market.base.transform(num_orders),
                                  prec=market.amount_precision)

    # compute costs
    amount_in_decimal = market.base.format(unit_amount)
    costs = [int(amount_in_decimal * p) for p in prices]

    # get average price for single order
    avg_price = market.quote.div(sum(prices),
                                 market.quote.transform(len(prices)),
                                 prec=market.price_precision)

    i("unit amount is {a}".format(a=market.base.print(unit_amount)))

    # send a single order if any of the costs is lower than market minimum
    if any(cost < market.cost_min for cost in costs):
        i("unitary cost is less than exchange minimum, creating single order")
        return create_order("limit", "sell", position, total_amount, avg_price)

    # avoid bucket rounding errors
    bucket_remainder = total_amount - sum([unit_amount] * num_orders)
    if bucket_remainder != 0:
        i("bucket remainder {r}".format(r=market.base.print(bucket_remainder)))

    # creates bucket orders if reached here, which normally it will
    for price in prices:
        if price == prices[-1]:
            unit_amount += bucket_remainder

        return create_order("limit", "sell", position, unit_amount, price)
