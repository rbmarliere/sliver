import datetime
import decimal
import time

import ccxt
import pandas
import peewee

import hypnox


def set_api(credential: hypnox.db.Credential):
    global api
    exchange = getattr(ccxt, credential.exchange.name)
    api = exchange({
        "apiKey": credential.api_key,
        "secret": credential.api_secret
    })
    api.set_sandbox_mode(True)
    # api.verbose = True


def get_latency():
    started = datetime.datetime.utcnow()

    api.fetch_time()

    elapsed = datetime.datetime.utcnow() - started
    elapsed_in_ms = int(elapsed.total_seconds() * 1000)

    hypnox.watchdog.log.info("api latency: " + str(elapsed_in_ms) + " ms")

    return elapsed_in_ms


def download(market: hypnox.db.Market, timeframe: str):
    # check if symbol is supported by exchange
    symbols = [pair["symbol"] for pair in api.fetch_markets()]
    assert market.symbol in symbols, (
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
            page = api.fetch_ohlcv(market.symbol,
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
            sleep_time = market.exchange.rate_limit
            hypnox.watchdog.log.info("rate limit exceeded, sleeping for " +
                                     str(sleep_time) + " seconds")
            time.sleep(sleep_time)
            continue

    # transform data for the database
    prices[0] = prices[0].apply(
        lambda x: datetime.datetime.utcfromtimestamp(x / 1000))
    prices[[1, 2, 3, 4]] = prices[[1, 2, 3,
                                   4]].applymap(lambda x: market.qtransform(x))
    prices[5] = prices[5].apply(lambda x: market.btransform(x))
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
                                            market.symbol)
            except ccxt.OrderNotFound:
                ex_order = api.fetch_order(order.exchange_order_id,
                                           market.symbol)

            amount = market.btransform(ex_order["amount"])
            cost = market.qtransform(ex_order["cost"])
            filled = market.btransform(ex_order["filled"])
            price = market.qtransform(ex_order["price"])

            hypnox.watchdog.log.info("cost: " + market.qprint(cost))
            hypnox.watchdog.log.info("filled: " + market.bprint(filled))

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
                order.fee = market.qtransform(ex_order["fee"]["cost"])

            position = order.position

            # update position info
            if order.side == "buy":
                position.bucket += order.cost
                position.entry_cost += order.cost
                position.entry_amount += order.filled
                position.fee += order.fee

                # update entry price if entry_amount is non zero
                if position.entry_amount > 0:
                    position.entry_price = market.qtransform(
                        (position.entry_cost / position.entry_amount))

            elif order.side == "sell":
                position.bucket += order.filled
                position.exit_amount += order.filled
                position.exit_cost += order.cost
                position.fee += order.fee

                # update exit price if exit_amount is non zero
                if position.exit_amount > 0:
                    position.exit_price = market.qtransform(
                        (position.exit_cost / position.exit_amount))

            order.save()
            position.save()


def create_order(side: hypnox.enum.OrderSide, position: hypnox.db.Position,
                 amount: int, price: int):
    market = position.user_strategy.strategy.market

    try:
        assert amount >= market.amount_min
        assert price >= market.price_min
        assert amount * price >= market.cost_min

        amount = market.bformat(amount)
        price = market.qformat(price)

        ex_order = api.create_order(market.symbol, "LIMIT_MAKER", side.value,
                                    amount, price)

        hypnox.watchdog.log.info(
            "created new " + side.value + " order:   " + market.symbol + " " +
            market.bprint(ex_order["amount"], False) + " @ " +
            market.qprint(ex_order["price"], False) + " (" +
            market.qprint(ex_order["amount"] * ex_order["price"], False) + ")")

    except ccxt.OrderImmediatelyFillable:
        hypnox.watchdog.log.warning(
            "order would be immediately fillable, skipping...")
        return
    except (ccxt.InvalidOrder, AssertionError):
        hypnox.watchdog.log.warning(
            "order values are smaller than exchange minimum, skipping...")
        return

    hypnox.db.Order.create_from_ex_order(ex_order, position)


def create_buy_orders(position: hypnox.db.Position, last_price: int,
                      num_orders: int, spread_pct: decimal.Decimal):
    market = position.user_strategy.strategy.market

    # remaining is a cost
    remaining = position.get_remaining_to_open()

    hypnox.watchdog.log.info("bucket amount is " +
                             market.qprint(position.bucket))
    hypnox.watchdog.log.info("remaining to fill bucket is " +
                             market.qprint(remaining))

    # compute price delta based on given spread
    delta = market.qdiv(last_price * spread_pct, 100)
    init_price = last_price - delta

    # compute cost for each order given a number of orders to create
    unit_cost = market.qdiv(remaining, num_orders)
    hypnox.watchdog.log.info("unit cost is " + market.qprint(unit_cost))

    # compute prices for each order
    unit_spread = market.qdiv(delta, num_orders)
    spreads = [init_price] + [unit_spread] * num_orders
    prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

    # check if current bucket is filled
    if (datetime.datetime.utcnow() < position.next_bucket
            and remaining < market.cost_min):
        hypnox.watchdog.log.info("bucket is full, skipping...")
        return

    # send a single order if cost of each order is lower than market minimum
    if unit_cost < market.cost_min:
        hypnox.watchdog.log.warning(
            "unitary cost is less than exchange minimum, "
            "creating single order")

        # get average price for single order
        avg_price = market.qdiv(sum(prices), len(prices))
        remaining_amount = market.bdiv(remaining, avg_price)
        create_order(hypnox.enum.OrderSide.BUY, position, remaining_amount,
                     avg_price)
        return

    # avoid rounding errors
    cost_remainder = remaining - sum([unit_cost] * num_orders)
    if cost_remainder != 0:
        hypnox.watchdog.log.warning("bucket remainder: " +
                                    market.qprint(cost_remainder))

    # creates bucket orders if reached here, which normally it will
    with hypnox.db.connection.atomic():
        for price in prices:
            amount = market.bdiv(unit_cost, price)

            if price == prices[-1]:
                amount += market.bdiv(cost_remainder, price)

            create_order(hypnox.enum.OrderSide.BUY, position, amount, price)


def create_sell_orders(position: hypnox.db.Position, last_price: int,
                       num_orders: int, spread_pct: decimal.Decimal):
    market = position.user_strategy.strategy.market

    # remaining is an amount
    remaining_to_fill = position.get_remaining_to_fill()
    remaining_to_exit = position.get_remaining_to_exit()

    hypnox.watchdog.log.info("bucket amount is " +
                             market.bprint(position.bucket))
    hypnox.watchdog.log.info("remaining to fill bucket is " +
                             market.bprint(remaining_to_fill))
    hypnox.watchdog.log.info("remaining to exit position is " +
                             market.bprint(remaining_to_exit))

    # compute price delta based on given spread
    delta = market.qdiv(last_price * spread_pct, 100)
    init_price = last_price + delta

    # compute prices for each order
    unit_spread = market.qdiv(-delta, num_orders)
    spreads = [init_price] + [unit_spread] * num_orders
    prices = [sum(spreads[:i]) for i in range(1, len(spreads))]

    # avoid position rounding errors by exiting early
    remaining = min(remaining_to_fill, remaining_to_exit)
    position_remainder = market.qformat(remaining_to_exit - remaining_to_fill)
    if (position_remainder > 0
            and position_remainder * prices[-1] <= market.cost_min):
        hypnox.watchdog.log.warning("position remainder: " +
                                    market.bprint(position_remainder, False))
        remaining = remaining_to_exit

    # compute amount for each order given a number of orders to create
    unit_amount = market.bdiv(remaining, num_orders)
    hypnox.watchdog.log.info("unit amount is " + market.bprint(unit_amount))

    # compute costs
    amount_in_decimal = market.bformat(unit_amount)
    costs = [int(amount_in_decimal * p) for p in prices]

    # get average price for single order
    avg_price = market.qdiv(sum(prices), len(prices))

    # check if current bucket is filled
    if (datetime.datetime.utcnow() < position.next_bucket
            and sum(costs) < market.cost_min):

        # if bucket is empty and cost is below minimum, position is stalled
        if position.bucket == 0:
            hypnox.watchdog.log.warning("position is stalled, exiting...")
            create_order(hypnox.enum.OrderSide.SELL, position,
                         remaining_to_exit, avg_price)
            return

        hypnox.watchdog.log.info("bucket is full, skipping...")
        return

    # send a single order if any of the costs is lower than market minimum
    if any(cost < market.cost_min for cost in costs):
        hypnox.watchdog.log.warning(
            "unitary cost is less than exchange minimum, "
            "creating single order")
        create_order(hypnox.enum.OrderSide.SELL, position, remaining,
                     avg_price)
        return

    # avoid bucket rounding errors
    bucket_remainder = remaining - sum([unit_amount] * num_orders)
    if bucket_remainder != 0:
        hypnox.watchdog.log.warning("bucket remainder: " +
                                    market.bprint(bucket_remainder))

    # creates bucket orders if reached here, which normally it will
    with hypnox.db.connection.atomic():
        for price in prices:
            if price == prices[-1]:
                unit_amount += bucket_remainder

            create_order(hypnox.enum.OrderSide.SELL, position, unit_amount,
                         price)


def refresh(user_strat: hypnox.db.UserStrategy):
    strategy = user_strat.strategy
    market = strategy.market

    # compute hypnox signal for given strategy
    # indicators = hypnox.strategy.get_indicators(strategy)
    # signal = indicators.iloc[-1].signal
    signal = hypnox.strategy.get_rsignal()

    # set timing variables
    now = datetime.datetime.utcnow()
    next_bucket = now + datetime.timedelta(minutes=strategy.bucket_interval)

    # fetch last price
    ticker = api.fetch_ticker(market.symbol)
    last_price = market.qtransform(ticker["last"])
    hypnox.watchdog.log.info("last price is " + market.qprint(last_price))

    # get current position for given user_strategy
    position = user_strat.get_active_position()

    if position is None:
        hypnox.watchdog.log.info("no active position")

    # if no position is found, create one if apt
    if position is None and signal == "buy":

        target_cost = hypnox.inventory.get_target_cost(market)
        bucket_max = market.qdiv(target_cost, strategy.num_orders)

        position = hypnox.db.Position(user_strategy=user_strat,
                                      next_bucket=next_bucket,
                                      bucket_max=bucket_max,
                                      status="opening",
                                      target_cost=target_cost)
        position.save()

        hypnox.watchdog.log.warning("** opened position " + str(position.id))
        hypnox.watchdog.log.info("target cost is " +
                                 market.qprint(target_cost))

        create_buy_orders(position, last_price, strategy.num_orders,
                          strategy.spread)
        return

    # return if no active position
    if position is None:
        return

    hypnox.watchdog.log.info("got '" + position.status + "' position " +
                             str(position.id) + " for market " + market.symbol)

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
            position.bucket_max = market.bdiv(position.entry_amount,
                                              strategy.num_orders)
            position.bucket = 0
            position.status = "closing"

    # TODO if is_closing() && signal == buy: buyback

    # close position if entry_cost is zero while closing it
    elif position.entry_cost == 0 and position.status == "closing":
        hypnox.watchdog.log.info("entry_cost is 0, closing position")
        position.status = "closed"

    # position finishes closing when exit equals entry
    amount_diff = position.entry_amount - position.exit_amount
    cost_diff = int(market.qformat(amount_diff * position.exit_price))
    if (position.exit_cost > 0 and position.status == "closing"
            and cost_diff < market.cost_min):
        position.status = "closed"
        position.pnl = (position.exit_cost - position.entry_cost -
                        position.fee)
        hypnox.watchdog.log.warning("position is now closed, pnl: " +
                                    market.qprint(position.pnl))

    # position finishes opening when it reaches target
    cost_diff = position.target_cost - position.entry_cost
    if position.status == "opening" and cost_diff < market.cost_min:
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
