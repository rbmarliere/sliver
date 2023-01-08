import datetime
import decimal
import time

import ccxt
import pandas
import peewee

import core


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
        core.watchdog.info("exchange does not have fetch_time")
        return

    api.fetch_time()

    elapsed = datetime.datetime.utcnow() - started
    elapsed_in_ms = int(elapsed.total_seconds() * 1000)

    core.watchdog.info("api latency is {l} ms".format(l=elapsed_in_ms))

    if elapsed_in_ms > 1500:
        core.watchdog.error("latency above threshold (1500)", None)
        raise ccxt.NetworkError


def download_prices(strategy: core.db.Strategy):
    now = datetime.datetime.utcnow()
    timeframe = strategy.timeframe
    market = strategy.market
    set_api(exchange=strategy.market.base.exchange)

    # check if symbol is supported by exchange
    symbols = [pair["symbol"] for pair in api.fetch_markets()]
    if market.get_symbol() not in symbols:
        core.watchdog.error("symbol not supported by exchange")
        raise ccxt.ExchangeError

    # check if timeframe is supported by exchange
    if timeframe not in api.timeframes:
        core.watchdog.error("timeframe not supported by exchange")
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
        core.watchdog.info(
            "no db entries found, downloading everything...")

    # return if last entry is last possible result
    if page_start + timeframe_delta > now:
        core.watchdog.info("price data is up to date")
        return

    prices = pandas.DataFrame(columns=[0, 1, 2, 3, 4, 5, 6, 7])
    while True:
        try:
            # api call with relevant params
            core.watchdog.info("downloading from {s}"
                               .format(s=page_start))
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
            core.watchdog.info("received data range {f} to {l}"
                               .format(f=page_first,
                                       l=page_last))

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
            core.watchdog.info("rate limit exceeded, sleeping for {s} seconds"
                               .format(s=sleep_time))
            time.sleep(sleep_time)
            continue

    # transform data for the database
    prices[0] = prices[0].apply(
        lambda x: datetime.datetime.utcfromtimestamp(x / 1000))
    prices[[1, 2, 3,
            4]] = prices[[1, 2, 3,
                          4]].applymap(lambda x: market.quote.transform(x))
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
    market = position.user_strategy.strategy.market
    symbol = market.get_symbol()

    # fetch internal open orders
    orders = position.get_open_orders()

    # if no orders found, exit
    if len(orders) == 0:
        core.watchdog.info("no open orders found")
        return

    for order in orders:
        core.watchdog.info("updating {s} order {i}"
                           .format(s=order.side,
                                   i=order.exchange_order_id))

        # cancel order first
        while True:
            try:
                ex_order = api.cancel_order(order.exchange_order_id, symbol)
                break
            except ccxt.OrderNotFound:
                break
            except ccxt.RequestTimeout as e:
                core.watchdog.error("order cancellation request timeout", e)
                # retry after 10 seconds
                time.sleep(10)

        while True:
            try:
                # fetch order to ensure its data is up to date
                ex_order = api.fetch_order(order.exchange_order_id, symbol)
                break
            except ccxt.RequestTimeout as e:
                core.watchdog.error("order fetch request timeout", e)
                # retry after 10 seconds
                time.sleep(10)

        order.sync(ex_order, position)


def create_order(type: str,
                 side: str,
                 position: core.db.Position,
                 amount: int,
                 price: int):
    market = position.user_strategy.strategy.market
    symbol = market.get_symbol()

    core.watchdog.info("attempt creation of {t} {s} order :: {a} @ {p}"
                       .format(t=type,
                               s=side,
                               a=market.base.print(amount),
                               p=market.quote.print(price)))
    try:
        assert amount >= market.amount_min
        assert price >= market.price_min
        assert amount * price >= market.cost_min
    except AssertionError:
        core.watchdog.info(
            "order values are smaller than exchange minimum, skipping...")
        return

    amount = market.base.format(amount)
    price = market.quote.format(price)

    inserted = False

    try:
        new_order = api.create_order(symbol,
                                     type,
                                     side,
                                     amount,
                                     price)
        inserted = True
        new_order_id = new_order["id"]

    except ccxt.InvalidOrder:
        core.watchdog.info(
            "invalid order parameters, skipping...")
        return

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
                core.watchdog.info("order was created and is open")
                new_order_id = last_order["id"]
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
                    core.watchdog.info("order was created and is closed")
                    new_order_id = last_order["id"]

    if inserted:
        core.watchdog.info("created new {t} {s} order {i}"
                           .format(t=type,
                                   s=side,
                                   i=new_order["id"]))
        while True:
            try:
                ex_order = api.fetch_order(new_order_id, symbol)
                core.db.Order.sync(core.db.Order(), ex_order, position)
                break
            except ccxt.NetworkError as e:
                core.watchdog.error("order fetch: network error", e)
                # retry after 10 seconds
                time.sleep(10)


def create_limit_buy_orders(total_cost: int,
                            position: core.db.Position,
                            last_price: int,
                            num_orders: int,
                            spread_pct: decimal.Decimal):

    market = position.user_strategy.strategy.market

    # compute price delta based on given spread
    delta = market.quote.div(last_price * spread_pct,
                             100,
                             trunc_precision=market.price_precision)
    init_price = last_price - delta

    # compute cost for each order given a number of orders to create
    unit_cost = market.quote.div(total_cost,
                                 num_orders,
                                 trunc_precision=market.price_precision)

    # compute prices for each order
    unit_spread = market.quote.div(delta,
                                   num_orders,
                                   trunc_precision=market.price_precision)
    spreads = [init_price] + [unit_spread] * num_orders
    prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

    core.watchdog.info("unit cost is {c}"
                       .format(c=market.quote.print(unit_cost)))

    # send a single order if cost of each order is lower than market minimum
    if unit_cost < market.cost_min:
        core.watchdog.info(
            "unitary cost is less than exchange minimum, creating single order"
        )

        # get average price for single order
        avg_price = market.quote.div(sum(prices),
                                     len(prices),
                                     trunc_precision=market.price_precision)
        total_amount = market.base.div(total_cost,
                                       avg_price,
                                       trunc_precision=market.amount_precision)
        create_order("limit", "buy", position, total_amount, avg_price)
        return

    # avoid rounding errors
    cost_remainder = total_cost - sum([unit_cost] * num_orders)
    if cost_remainder != 0:
        core.watchdog.info("bucket remainder: {r}"
                           .format(r=market.quote.print(cost_remainder)))

    # creates bucket orders if reached here, which normally it will
    for price in prices:
        amount = market.base.div(unit_cost,
                                 price,
                                 trunc_precision=market.amount_precision)

        if price == prices[-1]:
            amount += market.base.div(
                cost_remainder,
                price,
                trunc_precision=market.amount_precision)

        create_order("limit", "buy", position, amount, price)


def create_limit_sell_orders(total_amount: int,
                             position: core.db.Position,
                             last_price: int,
                             num_orders: int,
                             spread_pct: decimal.Decimal):

    market = position.user_strategy.strategy.market

    # compute price delta based on given spread
    delta = market.quote.div(last_price * spread_pct,
                             100,
                             trunc_precision=market.price_precision)
    init_price = last_price + delta

    # compute prices for each order
    unit_spread = market.quote.div(-delta,
                                   num_orders,
                                   trunc_precision=market.price_precision)
    spreads = [init_price] + [unit_spread] * num_orders
    prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

    # compute amount for each order given a number of orders to create
    unit_amount = market.base.div(total_amount,
                                  num_orders,
                                  trunc_precision=market.amount_precision)

    # compute costs
    amount_in_decimal = market.base.format(unit_amount)
    costs = [int(amount_in_decimal * p) for p in prices]

    # get average price for single order
    avg_price = market.quote.div(sum(prices),
                                 len(prices),
                                 trunc_precision=market.price_precision)

    core.watchdog.info("unit amount is {a}"
                       .format(a=market.base.print(unit_amount)))

    # send a single order if any of the costs is lower than market minimum
    if any(cost < market.cost_min for cost in costs):
        core.watchdog.info("unitary cost is less than exchange minimum, "
                           "creating single order")
        create_order("limit", "sell", position, total_amount, avg_price)
        return

    # avoid bucket rounding errors
    bucket_remainder = total_amount - sum([unit_amount] * num_orders)
    if bucket_remainder != 0:
        core.watchdog.info("bucket remainder: {r}"
                           .format(r=market.base.print(bucket_remainder)))

    # creates bucket orders if reached here, which normally it will
    for price in prices:
        if price == prices[-1]:
            unit_amount += bucket_remainder

        create_order("limit", "sell", position, unit_amount, price)


def refresh(position: core.db.Position):
    strategy = position.user_strategy.strategy
    signal = strategy.get_signal()
    market = strategy.market
    p = api.fetch_ticker(market.get_symbol())
    last_price = market.quote.transform(p["last"])

    core.watchdog.info("___________________________________________")
    core.watchdog.info("refreshing '{s}' position {i} for market {m}"
                       .format(s=position.status,
                               i=position.id,
                               m=market.get_symbol()))
    core.watchdog.info("last price is {p}"
                       .format(p=strategy.market.quote.print(last_price)))
    core.watchdog.info("target cost is {t}"
                       .format(t=market.quote.print(position.target_cost)))
    core.watchdog.info("entry cost is {t}"
                       .format(t=market.quote.print(position.entry_cost)))
    core.watchdog.info("exit cost is {t}"
                       .format(t=market.quote.print(position.exit_cost)))

    # if entry_cost is non-zero, check if position has to be closed
    if position.entry_cost > 0 and position.is_open():
        roi = round(((last_price / position.entry_price) - 1) * 100, 2)

        if (signal == "sell" or roi > strategy.stop_gain
                or roi < strategy.stop_loss * -1):
            core.watchdog.info("roi = {r}%".format(r=roi))
            core.watchdog.info(
                "minimum roi = {r}%".format(r=strategy.stop_gain))
            core.watchdog.info("stoploss = -{r}%".format(r=strategy.stop_loss))
            core.watchdog.info("closing position")
            core.watchdog.notice(position.get_notice(prefix="closing "))

            # when selling, bucket_max becomes an amount instead of cost
            position.bucket_max = market.base.div(
                position.entry_amount,
                strategy.num_orders,
                trunc_precision=market.amount_precision)
            position.bucket = 0
            position.status = "closing"

    # close position if entry_cost is zero while closing it or got sell signal
    elif (position.entry_cost == 0
          and (position.status == "closing" or signal == "sell")):
        core.watchdog.info("entry_cost is 0, position is now closed")
        position.status = "closed"

    if position.is_pending():
        now = datetime.datetime.utcnow()
        next_bucket = now + datetime.timedelta(
            minutes=strategy.bucket_interval)
        core.watchdog.info("next bucket starts at {t}"
                           .format(t=position.next_bucket))

        # check if current bucket needs to be reset
        if now > position.next_bucket:
            core.watchdog.info("moving on to next bucket")
            position.next_bucket = next_bucket
            position.bucket = 0

        # compute limit and market orders amounts or costs
        core.watchdog.info("limit to market ratio is {r}"
                           .format(r=strategy.lm_ratio))
        remaining = position.get_remaining(last_price)
        if strategy.lm_ratio == 1:
            market_total = remaining
            limit_total = 0
        elif strategy.lm_ratio > 0:
            if position.status == "opening":
                market_total = int(remaining * strategy.lm_ratio)
            elif position.status == "closing":
                market_total = int(remaining * strategy.lm_ratio)
            limit_total = remaining - market_total
        else:
            market_total = 0
            limit_total = remaining

        # check if theyre amounts or costs
        if position.status == "opening":
            remaining_cost = remaining
            market_total_cost = market_total
            limit_total_cost = limit_total
        elif position.status == "closing":
            remaining_cost = market.base.format(remaining) * last_price
            market_total_cost = market.base.format(market_total) * last_price
            limit_total_cost = market.base.format(limit_total) * last_price

        # check if current bucket is filled
        bucket_is_full = False
        if (datetime.datetime.utcnow() < position.next_bucket
                and remaining_cost < market.cost_min):
            core.watchdog.info("bucket is full")
            bucket_is_full = True

        # if bucket is not full but can't insert new orders, fill at market
        if (strategy.lm_ratio > 0
            and (market_total_cost < market.cost_min
                 or limit_total_cost < market.cost_min)):
            market_total = remaining
            limit_total = 0

    # create buy orders for an opening position
    if position.status == "opening" and not bucket_is_full:
        if market_total > 0:
            # market_total is a cost
            market_total = market.base.div(market_total, last_price)
            create_order("market", "buy", position, market_total, last_price)

        if limit_total > 0:
            create_limit_buy_orders(limit_total,
                                    position,
                                    last_price,
                                    strategy.num_orders,
                                    strategy.spread)

    # create sell orders for a closing position or close
    elif position.status == "closing" and not bucket_is_full:
        if market_total > 0:
            # market_total is an amount
            create_order("market", "sell", position, market_total, last_price)

        if limit_total > 0:
            create_limit_sell_orders(limit_total,
                                     position,
                                     last_price,
                                     strategy.num_orders,
                                     strategy.spread)

    # position finishes closing when exit equals entry
    amount_diff = position.entry_amount - position.exit_amount
    cost_diff = int(market.quote.format(amount_diff * position.exit_price))
    if (position.exit_cost > 0 and position.status == "closing"
            and cost_diff < market.cost_min):
        position.status = "closed"
        position.pnl = (position.exit_cost
                        - position.entry_cost
                        - position.fee)
        core.watchdog.info("position is now closed, pnl: {r}"
                           .format(r=market.quote.print(position.pnl)))
        core.watchdog.notice(position.get_notice(prefix="closed "))

    # position finishes opening when it reaches target
    cost_diff = position.target_cost - position.entry_cost
    if (position.status == "opening" and position.entry_cost > 0
            and cost_diff < market.cost_min):
        position.status = "open"
        core.watchdog.info("position is now open")
        core.watchdog.notice(position.get_notice(suffix="is now open"))

    position.save()
