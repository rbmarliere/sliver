import datetime
import decimal
import time

import ccxt
import pandas
import peewee

import hypnox


def set_api(new_cred: hypnox.db.Credential):
    global credential
    if 'credential' in globals() and new_cred == credential:
        return

    credential = new_cred

    global api
    exchange = getattr(ccxt, new_cred.exchange.name)
    api = exchange({"apiKey": new_cred.api_key, "secret": new_cred.api_secret})
    api.set_sandbox_mode(True)
    # api.verbose = True

    # check if exchange is alive
    check_latency()


def check_latency():
    started = datetime.datetime.utcnow()

    api.fetch_time()

    elapsed = datetime.datetime.utcnow() - started
    elapsed_in_ms = int(elapsed.total_seconds() * 1000)

    hypnox.watchdog.log.info("api latency: " + str(elapsed_in_ms) + " ms")

    if elapsed_in_ms > 1500:
        hypnox.watchdog.log.info("latency above threshold (1500)")
        raise ccxt.NetworkError


def download(market: hypnox.db.Market, timeframe: str):
    # check if symbol is supported by exchange
    symbols = [pair["symbol"] for pair in api.fetch_markets()]
    assert market.get_symbol() in symbols, (
        "symbol not supported by exchange! possible values are " +
        str(symbols))

    # check if timeframe is supported by exchange
    assert timeframe in api.timeframes, (
        "timeframe not supported by exchange! possible values are " +
        str([*api.timeframes]))

    timeframe_delta = hypnox.utils.get_timeframe_delta(timeframe)
    page_size = 500

    # fetch first and last price entries from the db
    try:
        filter = ((hypnox.db.Price.market == market) &
                  (hypnox.db.Price.timeframe == timeframe))
        asc = hypnox.db.Price.time.asc()
        desc = hypnox.db.Price.time.desc()
        first_entry = hypnox.db.Price.select().where(filter).order_by(
            asc).get().time
        last_entry = hypnox.db.Price.select().where(filter).order_by(
            desc).get().time
        page_start = last_entry
    except peewee.DoesNotExist:
        first_entry = datetime.datetime.fromtimestamp(0)
        last_entry = datetime.datetime.fromtimestamp(0)
        page_start = datetime.datetime(2000, 1, 1)
        hypnox.watchdog.log.info(
            "no db entries found, downloading everything...")

    # conditional to see up to where to insert or begin from
    stop_at_first = False
    if first_entry > page_start:
        stop_at_first = True
    elif last_entry > page_start:
        page_start = last_entry + timeframe_delta

    # return if last entry is last possible result
    if last_entry + timeframe_delta > datetime.datetime.utcnow():
        hypnox.watchdog.log.info(
            "price data is already up to date, skipping...")
        return

    prices = pandas.DataFrame(columns=[0, 1, 2, 3, 4, 5, 6, 7])
    while True:
        try:
            # api call with relevant params
            hypnox.watchdog.log.info("downloading from " + str(page_start))
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
            hypnox.watchdog.log.info("received data range " + str(page_first) +
                                     " to " + str(page_last))

            # concatenating existing pages with current page
            prices = pandas.concat(
                [prices, pandas.DataFrame.from_records(page)])

            # only store up until last stored entry
            if stop_at_first and page_last > first_entry:
                for p in page:
                    curr = datetime.datetime.utcfromtimestamp(p[0] / 1000)
                    if curr >= first_entry:
                        prices = prices[prices[0] < p[0]]
                        break
                page_start = last_entry + timeframe_delta
                stop_at_first = False
                continue

            # break if received page is less than max size
            if len(page) < page_size:
                break

            # increment the counter
            page_start = page_last + timeframe_delta

        except ccxt.RateLimitExceeded:
            sleep_time = market.base.exchange.rate_limit
            hypnox.watchdog.log.info("rate limit exceeded, sleeping for " +
                                     str(sleep_time) + " seconds")
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

    # insert into the database
    with hypnox.db.connection.atomic():
        hypnox.db.Price.insert_many(
            prices.values.tolist(),
            fields=[
                hypnox.db.Price.time, hypnox.db.Price.open,
                hypnox.db.Price.high, hypnox.db.Price.low,
                hypnox.db.Price.close, hypnox.db.Price.volume,
                hypnox.db.Price.timeframe, hypnox.db.Price.market
            ]).execute()


def sync_orders(position: hypnox.db.Position):
    market = position.user_strategy.strategy.market

    # fetch internal open orders
    orders = position.get_open_orders()

    # if no orders found, exit
    if len(orders) == 0:
        hypnox.watchdog.log.info("no open orders found")
        return

    with hypnox.db.connection.atomic():
        for order in orders:
            hypnox.watchdog.log.info("updating " + order.side + " order " +
                                     str(order.exchange_order_id))

            # fetch each order to sync
            try:
                ex_order = api.cancel_order(order.exchange_order_id,
                                            market.get_symbol())
            except ccxt.OrderNotFound:
                ex_order = api.fetch_order(order.exchange_order_id,
                                           market.get_symbol())

            amount = market.base.transform(ex_order["amount"])
            cost = market.quote.transform(ex_order["cost"])
            filled = market.base.transform(ex_order["filled"])
            price = market.quote.transform(ex_order["price"])

            hypnox.watchdog.log.info(
                market.base.print(filled) + " @ " + market.quote.print(price) +
                " (" + market.quote.print(cost) + ")")

            # update order info
            order.status = ex_order["status"]
            order.amount = amount
            order.cost = cost
            order.filled = filled
            order.price = price

            # check for fees
            if ex_order["fee"] is None:
                order.fee = 0
            else:
                order.fee = market.quote.transform(ex_order["fee"]["cost"])

            position = order.position

            # update position info
            if order.side == "buy":
                position.bucket += order.cost
                position.entry_cost += order.cost
                position.entry_amount += order.filled
                position.fee += order.fee

                # update entry price if entry_amount is non zero
                if position.entry_amount > 0:
                    position.entry_price = market.quote.transform(
                        (position.entry_cost / position.entry_amount))

            elif order.side == "sell":
                position.bucket += order.filled
                position.exit_amount += order.filled
                position.exit_cost += order.cost
                position.fee += order.fee

                # update exit price if exit_amount is non zero
                if position.exit_amount > 0:
                    position.exit_price = market.quote.transform(
                        (position.exit_cost / position.exit_amount))

            order.save()
            position.save()

    return position


def create_order(side: str, position: hypnox.db.Position, amount: int,
                 price: int):
    market = position.user_strategy.strategy.market

    try:
        assert amount >= market.amount_min
        assert price >= market.price_min
        assert amount * price >= market.cost_min

        amount = market.base.format(amount)
        price = market.quote.format(price)

        ex_order = api.create_order(market.get_symbol(), "LIMIT_MAKER", side,
                                    amount, price)

        hypnox.watchdog.log.info("created new " + side + " order " +
                                 str(ex_order["id"]))
        hypnox.watchdog.log.info(
            market.base.print(ex_order["amount"], False) + " @ " +
            market.quote.print(ex_order["price"], False) + " (" +
            market.quote.print(ex_order["amount"] * ex_order["price"], False) +
            ")")

    except ccxt.OrderImmediatelyFillable:
        hypnox.watchdog.log.info(
            "order would be immediately fillable, skipping...")
        return
    except (ccxt.InvalidOrder, AssertionError):
        hypnox.watchdog.log.info(
            "order values are smaller than exchange minimum, skipping...")
        return

    hypnox.db.Order.create_from_ex_order(ex_order, position)


def create_buy_orders(position: hypnox.db.Position, last_price: int,
                      num_orders: int, spread_pct: decimal.Decimal):
    market = position.user_strategy.strategy.market

    # remaining is a cost
    remaining = position.get_remaining_to_open()

    hypnox.watchdog.log.info("bucket amount is " +
                             market.quote.print(position.bucket))
    hypnox.watchdog.log.info("remaining to fill bucket is " +
                             market.quote.print(remaining))

    # compute price delta based on given spread
    delta = market.quote.div(last_price * spread_pct,
                             100,
                             trunc_precision=market.price_precision)
    init_price = last_price - delta

    # compute cost for each order given a number of orders to create
    unit_cost = market.quote.div(remaining,
                                 num_orders,
                                 trunc_precision=market.price_precision)
    hypnox.watchdog.log.info("unit cost is " + market.quote.print(unit_cost))

    # compute prices for each order
    unit_spread = market.quote.div(delta,
                                   num_orders,
                                   trunc_precision=market.price_precision)
    spreads = [init_price] + [unit_spread] * num_orders
    prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

    # check if current bucket is filled
    if (datetime.datetime.utcnow() < position.next_bucket
            and remaining < market.cost_min):
        hypnox.watchdog.log.info("bucket is full, skipping...")
        return

    # send a single order if cost of each order is lower than market minimum
    if unit_cost < market.cost_min:
        hypnox.watchdog.log.info(
            "unitary cost is less than exchange minimum, creating single order"
        )

        # get average price for single order
        avg_price = market.quote.div(sum(prices),
                                     len(prices),
                                     trunc_precision=market.price_precision)
        remaining_amount = market.base.div(
            remaining, avg_price, trunc_precision=market.amount_precision)
        create_order("buy", position, remaining_amount, avg_price)
        return

    # avoid rounding errors
    cost_remainder = remaining - sum([unit_cost] * num_orders)
    if cost_remainder != 0:
        hypnox.watchdog.log.info("bucket remainder: " +
                                 market.quote.print(cost_remainder))

    # creates bucket orders if reached here, which normally it will
    with hypnox.db.connection.atomic():
        for price in prices:
            amount = market.base.div(unit_cost,
                                     price,
                                     trunc_precision=market.amount_precision)

            if price == prices[-1]:
                amount += market.base.div(
                    cost_remainder,
                    price,
                    trunc_precision=market.amount_precision)

            create_order("buy", position, amount, price)


def create_sell_orders(position: hypnox.db.Position, last_price: int,
                       num_orders: int, spread_pct: decimal.Decimal):
    market = position.user_strategy.strategy.market

    # remaining is an amount
    remaining_to_fill = position.get_remaining_to_fill()
    remaining_to_exit = position.get_remaining_to_exit()

    hypnox.watchdog.log.info("bucket amount is " +
                             market.base.print(position.bucket))
    hypnox.watchdog.log.info("remaining to fill bucket is " +
                             market.base.print(remaining_to_fill))
    hypnox.watchdog.log.info("remaining to exit position is " +
                             market.base.print(remaining_to_exit))

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

    # avoid position rounding errors by exiting early
    remaining = min(remaining_to_fill, remaining_to_exit)
    position_remainder = market.quote.format(remaining_to_exit -
                                             remaining_to_fill)
    if (position_remainder > 0
            and position_remainder * prices[-1] <= market.cost_min):
        hypnox.watchdog.log.info("position remainder: " +
                                 market.base.print(position_remainder, False))
        remaining = remaining_to_exit

    # compute amount for each order given a number of orders to create
    unit_amount = market.base.div(remaining,
                                  num_orders,
                                  trunc_precision=market.amount_precision)
    hypnox.watchdog.log.info("unit amount is " +
                             market.base.print(unit_amount))

    # compute costs
    amount_in_decimal = market.base.format(unit_amount)
    costs = [int(amount_in_decimal * p) for p in prices]

    # get average price for single order
    avg_price = market.quote.div(sum(prices),
                                 len(prices),
                                 trunc_precision=market.price_precision)

    # check if current bucket is filled
    if (datetime.datetime.utcnow() < position.next_bucket
            and sum(costs) < market.cost_min):

        # if bucket is empty and cost is below minimum, position is stalled
        if position.bucket == 0:
            hypnox.watchdog.log.info("position is stalled, exiting...")
            create_order("sell", position, remaining_to_exit, avg_price)
            return

        hypnox.watchdog.log.info("bucket is full, skipping...")
        return

    # send a single order if any of the costs is lower than market minimum
    if any(cost < market.cost_min for cost in costs):
        hypnox.watchdog.log.info("unitary cost is less than exchange minimum, "
                                 "creating single order")
        create_order("sell", position, remaining, avg_price)
        return

    # avoid bucket rounding errors
    bucket_remainder = remaining - sum([unit_amount] * num_orders)
    if bucket_remainder != 0:
        hypnox.watchdog.log.info("bucket remainder: " +
                                 market.base.print(bucket_remainder))

    # creates bucket orders if reached here, which normally it will
    with hypnox.db.connection.atomic():
        for price in prices:
            if price == prices[-1]:
                unit_amount += bucket_remainder

            create_order("sell", position, unit_amount, price)


def refresh(position: hypnox.db.Position, signal: str, last_price: int):
    strategy = position.user_strategy.strategy
    market = strategy.market
    now = datetime.datetime.utcnow()
    next_bucket = now + datetime.timedelta(minutes=strategy.bucket_interval)

    hypnox.watchdog.log.info("refreshing '" + position.status + "' position " +
                             str(position.id) + " for market " +
                             market.get_symbol())

    # check if current bucket needs to be reset
    if now > position.next_bucket:
        hypnox.watchdog.log.info("moving on to next bucket")
        position.next_bucket = next_bucket
        position.bucket = 0

    hypnox.watchdog.log.info("next bucket starts at " +
                             str(position.next_bucket))

    # if entry_cost is non-zero, check if position has to be closed
    if position.entry_cost > 0 and position.is_open():
        roi = round(((last_price / position.entry_price) - 1) * 100, 2)
        hypnox.watchdog.log.info("roi = " + str(roi) + "%")
        hypnox.watchdog.log.info("minimum roi = " + str(strategy.min_roi) +
                                 "%")
        hypnox.watchdog.log.info("stop loss = " + str(strategy.stop_loss) +
                                 "%")

        if (signal == "sell" or roi > strategy.min_roi
                or roi < strategy.stop_loss * -1):
            hypnox.watchdog.log.info("closing position")

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
        hypnox.watchdog.log.info("entry_cost is 0, position is now closed")
        position.status = "closed"

    # position finishes closing when exit equals entry
    amount_diff = position.entry_amount - position.exit_amount
    cost_diff = int(market.quote.format(amount_diff * position.exit_price))
    if (position.exit_cost > 0 and position.status == "closing"
            and cost_diff < market.cost_min):
        position.status = "closed"
        position.pnl = (position.exit_cost - position.entry_cost -
                        position.fee)
        hypnox.watchdog.log.info("position is now closed, pnl: " +
                                 market.quote.print(position.pnl))

    # position finishes opening when it reaches target
    cost_diff = position.target_cost - position.entry_cost
    if (position.status == "opening" and position.entry_cost > 0
            and cost_diff < market.cost_min):
        position.status = "open"
        hypnox.watchdog.log.info("position is now open")

    # create buy orders for an opening position
    if position.status == "opening":
        create_buy_orders(position, last_price, strategy.num_orders,
                          strategy.spread)

    # create sell orders for a closing position or close
    elif position.status == "closing":
        create_sell_orders(position, last_price, strategy.num_orders,
                           strategy.spread)

    else:
        hypnox.watchdog.log.info("position is " + position.status +
                                 ", skipping order creation...")

    position.save()
