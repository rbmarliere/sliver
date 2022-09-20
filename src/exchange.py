import datetime
import re
import time
from decimal import Decimal as Dec

import ccxt
import pandas
import peewee

import src as hypnox

# TODO refactor + comments
# TODO param. Dec(0.98)

# TODO catch ALL api errors
# https://docs.ccxt.com/en/latest/manual.html?#exception-hierarchy
# TODO catch db errors, failsafe atomic() etc

api = ccxt.binance({
    "apiKey": hypnox.config.config["BINANCE_KEY"],
    "secret": hypnox.config.config["BINANCE_SECRET"],
})
# api.set_sandbox_mode(True)
# api.verbose = True


def check_api():
    print("check_api")


def download(args):
    # check if symbol is supported by exchange
    symbols = [pair["symbol"] for pair in api.fetch_markets()]
    if args.symbol not in symbols:
        hypnox.watchdog.log.error(
            "symbol not supported by exchange! possible values are " +
            str(symbols))
        return 1

    # check if timeframe is supported by exchange
    if args.timeframe not in api.timeframes:
        hypnox.watchdog.log.error(
            "timeframe not supported by exchange! possible values are " +
            str([*api.timeframes]))
        return 1

    # set needed variables
    sleep_time = (api.rateLimit / 1000) + 1
    page_size = 500
    timeframe = hypnox.utils.get_timeframe_delta(args.timeframe)

    # fetch first and last price entries from the db
    try:
        filter = ((hypnox.db.Price.symbol == args.symbol) &
                  (hypnox.db.Price.timeframe == args.timeframe))
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
        page_start = last_entry + timeframe

    prices = pandas.DataFrame(columns=[0, 1, 2, 3, 4, 5, 6, 7, 8])
    while True:
        try:
            # api call with relevant params
            hypnox.watchdog.log.info("downloading from " + str(page_start))
            page = api.fetch_ohlcv(args.symbol,
                                   since=int(page_start.timestamp() * 1000),
                                   timeframe=args.timeframe,
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
                page_start = last_entry + timeframe
                stop_at_first = False
                continue

            # break if received page is less than max size
            if len(page) < page_size:
                break

            # increment the counter
            page_start = page_last + timeframe

        except ccxt.RateLimitExceeded:
            hypnox.watchdog.log.info("rate limit exceeded, sleeping for " +
                                     str(sleep_time) + " seconds")
            time.sleep(sleep_time)
            continue

    # transform data for the database
    prices[0] = prices[0].apply(
        lambda x: datetime.datetime.utcfromtimestamp(x / 1000))
    prices[6] = args.symbol
    prices[7] = args.timeframe
    prices[8] = api.id

    # insert into the database
    with hypnox.db.connection.atomic():
        hypnox.db.Price.insert_many(
            prices.values.tolist(),
            fields=[
                hypnox.db.Price.time, hypnox.db.Price.open,
                hypnox.db.Price.high, hypnox.db.Price.low,
                hypnox.db.Price.close, hypnox.db.Price.volume,
                hypnox.db.Price.symbol, hypnox.db.Price.timeframe,
                hypnox.db.Price.exchange
            ]).execute()


def sync_orders(symbol):
    try:
        # cancel all open orders so they can't be modified from here
        hypnox.watchdog.log.info("canceling all orders")
        api.cancel_all_orders(symbol)
    except ccxt.OrderNotFound:
        hypnox.watchdog.log.info("no orders to cancel")

    # grab internal open orders
    orders = hypnox.db.get_open_orders(symbol)
    if len(orders) == 0:
        return
    with hypnox.db.connection.atomic():
        for order in orders:
            # fetch each order to sync, make sure they're not open
            hypnox.watchdog.log.info("updating " + order.side + " order " +
                                     str(order.exchange_order_id))
            ex_order = api.fetch_order(order.exchange_order_id, symbol)
            if ex_order["status"] == "open":
                try:
                    hypnox.watchdog.log.info("order is open, canceling...")
                    ex_order = api.cancel_order(order.exchange_order_id,
                                                symbol)
                except ccxt.OrderNotFound:
                    hypnox.watchdog.log.info("order changed, refetching...")
                    ex_order = api.fetch_order(order.exchange_order_id)

            # update order amounts
            if order.cost != ex_order["cost"]:
                hypnox.watchdog.log.info("old cost: " +
                                         str(float(round(order.cost, 2))) +
                                         " new cost: " +
                                         str(round(ex_order["cost"], 2)))
            order.status = ex_order["status"]
            order.cost = Dec(ex_order["cost"])
            order.filled = Dec(ex_order["filled"])

            # update position info
            position = order.position
            if order.side == "buy":
                try:
                    order.fee += (Dec(ex_order["fee"]["cost"]) *
                                  Dec(ex_order["price"]))
                except TypeError:
                    pass
                position.bucket += order.cost
                position.entry_cost += order.cost
                position.entry_amount += Dec(order.filled)
                position.fee += order.fee
                if position.entry_amount > 0:
                    position.entry_price = (position.entry_cost /
                                            position.entry_amount)
                if position.entry_cost >= position.target_cost * Dec(0.98):
                    # TODO proper inventory management
                    position.status = "open"

            elif order.side == "sell":
                try:
                    order.fee += Dec(ex_order["fee"]["cost"])
                except TypeError:
                    pass
                position.bucket += order.filled
                position.exit_amount += order.filled
                position.exit_cost += order.cost
                position.fee += order.fee
                if position.exit_amount > 0:
                    position.exit_price = (position.exit_cost /
                                           position.exit_amount)
                if position.exit_amount >= position.entry_amount * Dec(0.98):
                    # TODO proper inventory management
                    position.status = "closed"
                    position.pnl = (position.exit_cost - position.entry_cost -
                                    position.fee)
                    hypnox.watchdog.log.info("position is now closed, PnL: " +
                                             str(round(position.pnl, 2)))

            order.save()
            position.save()


def create_buy_orders(strategy, position, last_price):
    prices = []
    delta = last_price * Dec(strategy["SPREAD_PERCENTAGE"])
    n_orders = strategy["NUM_ORDERS"]

    init_price = last_price - delta
    prices = [init_price] + [delta / n_orders] * n_orders
    prices = [round(sum(prices[:i]), 2) for i in range(1, len(prices))]

    unit_cost = Dec(position.get_remaining_to_open() / n_orders)

    with hypnox.db.connection.atomic():
        for price in prices:
            amount = round(unit_cost / Dec(price), 8)
            hypnox.watchdog.log.info("creating new buy order: " +
                                     position.symbol + " " + str(amount) +
                                     " @ " + str(price) + " (" +
                                     str(round(unit_cost, 2)) + ")")
            try:
                # TODO catch invalidquantity, if so market buy
                ex_order = api.create_order(position.symbol, "LIMIT_MAKER",
                                            "buy", amount, price)
            except ccxt.OrderImmediatelyFillable:
                continue

            try:
                ex_order["fee"] = (Dec(ex_order["fee"]["cost"]) *
                                   Dec(ex_order["price"]))
            except TypeError:
                ex_order["fee"] = 0

            hypnox.db.Order.create_from_ex_order(ex_order, position)


def create_sell_orders(strategy, position, last_price):
    prices = []
    delta = last_price * Dec(strategy["SPREAD_PERCENTAGE"])
    n_orders = strategy["NUM_ORDERS"]

    init_price = last_price + delta
    prices = [init_price] + [-delta / n_orders] * n_orders
    prices = [round(sum(prices[:i]), 2) for i in range(1, len(prices))]

    amount = round(Dec(position.get_remaining_to_close() / n_orders), 8)

    with hypnox.db.connection.atomic():
        for price in prices:
            hypnox.watchdog.log.info("creating new sell order: " +
                                     position.symbol + " " + str(amount) +
                                     " @ " + str(price) + " (" +
                                     str(round(amount * price, 2)) + ")")
            try:
                # TODO catch invalidquantity, if so market sell
                ex_order = api.create_order(position.symbol, "LIMIT_MAKER",
                                            "sell", amount, price)
            except ccxt.OrderImmediatelyFillable:
                continue
            except ccxt.InvalidOrder as e:
                hypnox.watchdog.log.warning(
                    "order is below minimum required, creating single order")
                if re.search("MIN_NOTIONAL", e.args[0]):
                    ex_order = api.create_order(
                        position.symbol, "LIMIT_MAKER", "sell",
                        position.get_remaining_to_close(), price)
                    # prices = [price]
                    try:
                        ex_order["fee"] = Dec(ex_order["fee"]["cost"])
                    except TypeError:
                        ex_order["fee"] = 0
                    hypnox.db.Order.create_from_ex_order(ex_order, position)
                    break

            try:
                ex_order["fee"] = Dec(ex_order["fee"]["cost"])
            except TypeError:
                ex_order["fee"] = 0
            hypnox.db.Order.create_from_ex_order(ex_order, position)


def refresh(args):
    strategy = hypnox.config.StrategyConfig(args.strategy).config
    indicators = hypnox.strategy.get_indicators(strategy)
    signal = indicators.iloc[-1].signal

    now = datetime.datetime.utcnow()
    next_bucket = now + datetime.timedelta(
        minutes=strategy["BUCKET_TIMEDELTA_IN_MINUTES"])

    ticker = api.fetch_ticker(strategy["SYMBOL"])
    last_price = Dec(ticker["last"])
    hypnox.watchdog.log.info("last price is " + str(round(last_price, 2)))

    try:
        position = hypnox.db.get_active_position(strategy["SYMBOL"]).get()
        hypnox.watchdog.log.info("got position " + str(position.id))

        if now > position.next_bucket:
            hypnox.watchdog.log.info("moving on to next bucket")
            position.next_bucket = next_bucket
            position.bucket = 0
            position.save()
        hypnox.watchdog.log.info("next bucket starts at " +
                                 str(position.next_bucket))

        if position.entry_cost > 0:
            curr_roi = (last_price * position.entry_amount /
                        position.entry_cost) - 1
            if (signal == "sell" or curr_roi >= strategy["MINIMUM_ROI"]
                    or curr_roi <= strategy["STOP_LOSS"]):
                hypnox.watchdog.log.info("roi = " +
                                         str(round(curr_roi * 100, 2)) + "%")
                hypnox.watchdog.log.info("closing position")
                # TODO proper inventory logic
                position.bucket_max = round(
                    position.entry_amount / strategy["NUM_ORDERS"], 8)
                position.status = "closing"
                position.save()
        elif position.entry_cost == 0 and position.status == "closing":
            hypnox.watchdog.log.info("entry_cost is 0, closing position")
            position.status = "closed"
            position.save()

        if position.status == "opening":
            hypnox.watchdog.log.info("bucket cost is " + str(position.bucket))
            hypnox.watchdog.log.info("remaining to fill in bucket is " +
                                     str(position.get_remaining_to_open()))
            if (datetime.datetime.utcnow() < position.next_bucket
                    and position.get_remaining_to_open() <= 1):
                # TODO remaining should consider api.minimum_quantity
                hypnox.watchdog.log.info("bucket is full, skipping...")
                return
            create_buy_orders(strategy, position, last_price)
        elif position.status == "closing":
            # TODO what if its closing and receives buy signal?
            # currently nothing happens, it will keep closing
            hypnox.watchdog.log.info("bucket amount is " +
                                     str(position.bucket))
            hypnox.watchdog.log.info("remaining to fill in bucket is " +
                                     str(position.get_remaining_to_close()))
            if (datetime.datetime.utcnow() < position.next_bucket
                    and position.get_remaining_to_close() <= 0.00100000):
                # TODO remaining should consider api.minimum_quantity
                hypnox.watchdog.log.info("bucket is full, skipping...")
                return
            create_sell_orders(strategy, position, last_price)
        else:
            hypnox.watchdog.log.info("position is " + position.status +
                                     ", skipping order creation...")
    except peewee.DoesNotExist:
        hypnox.watchdog.log.info("no active position")
        if signal == "buy":
            target_cost, bucket_max = hypnox.inventory.get_inventory(strategy)
            hypnox.watchdog.log.info("opening position")
            hypnox.watchdog.log.info("target cost is " + str(target_cost))
            hypnox.watchdog.log.info("remaining to fill in bucket is " +
                                     str(bucket_max))
            position = hypnox.db.Position(exchange=api.id,
                                          symbol=strategy["SYMBOL"],
                                          next_bucket=next_bucket,
                                          bucket_max=bucket_max,
                                          bucket=0,
                                          status="opening",
                                          target_cost=target_cost)
            position.save()
            create_buy_orders(strategy, position, last_price)
