import datetime
import logging
import time
from decimal import Decimal as Dec

import ccxt
import pandas
import peewee

import src as hypnox

# TODO: param. Dec(0.98)
# TODO: catch exchange errors
# https://docs.ccxt.com/en/latest/manual.html?#exception-hierarchy
# TODO: catch db errors, failsafe atomic() etc

exchange = ccxt.binance({
    "apiKey": hypnox.config.config["BINANCE_KEY"],
    "secret": hypnox.config.config["BINANCE_SECRET"],
})
exchange.set_sandbox_mode(True)
# exchange.verbose = True


def download(args):
    sleep_time = (exchange.rateLimit / 1000) + 1
    page_size = 500
    page_start = int(datetime.datetime(2011, 6, 1).timestamp() * 1000)
    timeframe = 4 * 60 * 60 * 1000  # 4h in millisecs

    try:
        first_entry = int(hypnox.db.Price.select().order_by(
            hypnox.db.Price.time.asc()).get().time.timestamp() * 1000)
        last_entry = int(hypnox.db.Price.select().order_by(
            hypnox.db.Price.time.desc()).get().time.timestamp() * 1000)
    except peewee.DoesNotExist:
        first_entry = 0
        last_entry = 0
        logging.info("no db entries found, downloading everything...")

    stop_at_first = False
    if first_entry > page_start:
        stop_at_first = True
    elif last_entry > page_start:
        page_start = last_entry + timeframe

    prices = pandas.DataFrame(columns=[0, 1, 2, 3, 4, 5])
    while True:
        try:
            logging.info("downloading from " +
                         str(datetime.datetime.fromtimestamp(page_start /
                                                             1000)))
            page = exchange.fetch_ohlcv("BTC/USDT",
                                        since=page_start,
                                        timeframe="4h",
                                        limit=page_size)
            prices = pandas.concat(
                [prices, pandas.DataFrame.from_records(page)])

            if stop_at_first and page[-1][0] > first_entry:
                for p in page:
                    if p[0] >= first_entry:
                        prices = prices[prices[0] < p[0]]
                        break
                page_start = last_entry + timeframe
                stop_at_first = False
                continue

            if len(page) < page_size:
                break

            page_start = page[-1][0] + timeframe
        except ccxt.RateLimitExceeded:
            logging.info("rate limit exceeded, sleeping for " +
                         str(sleep_time) + " seconds")
            time.sleep(sleep_time)
            continue

    prices[0] = prices[0].apply(
        lambda x: datetime.datetime.fromtimestamp(x / 1000))

    with hypnox.db.connection.atomic():
        hypnox.db.Price.insert_many(
            prices.values.tolist(),
            fields=[
                hypnox.db.Price.time, hypnox.db.Price.open,
                hypnox.db.Price.high, hypnox.db.Price.low,
                hypnox.db.Price.close, hypnox.db.Price.volume
            ]).execute()


def sync_orders(symbol):
    try:
        # cancel all open orders so they can't be modified from here
        logging.info("canceling all orders")
        exchange.cancel_all_orders(symbol)
    except ccxt.OrderNotFound:
        logging.info("no orders to cancel")

    # grab internal open orders
    orders = hypnox.db.get_open_orders(symbol)
    with hypnox.db.connection.atomic():
        for order in orders:
            # fetch each order to sync, make sure they're not open
            logging.info("updating order " + str(order.exchange_order_id))
            ex_order = exchange.fetch_order(order.exchange_order_id, symbol)
            if ex_order["status"] == "open":
                try:
                    logging.info("order is open, canceling...")
                    ex_order = exchange.cancel_order(order.exchange_order_id,
                                                     symbol)
                except ccxt.OrderNotFound:
                    logging.info("order changed, refetching...")
                    ex_order = exchange.fetch_order(order.exchange_order_id)

            # update order amounts
            if order.cost != ex_order["cost"]:
                logging.info("old cost: " + str(float(order.cost)) +
                             " new cost: " + str(ex_order["cost"]))
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
                position.window_cost += order.cost
                position.entry_cost += order.cost
                position.entry_amount += Dec(order.filled)
                position.fee += order.fee
                if position.entry_amount > 0:
                    position.entry_price = (position.entry_cost /
                                            position.entry_amount)
                if position.entry_cost >= position.target_cost * Dec(0.98):
                    position.status = "open"

            elif order.side == "sell":
                try:
                    order.fee += Dec(ex_order["fee"]["cost"])
                except TypeError:
                    pass
                position.window_cost += order.cost
                position.exit_amount += order.filled
                position.exit_cost += order.cost
                position.fee += order.fee
                if position.exit_amount > 0:
                    position.exit_price = (position.exit_cost /
                                           position.exit_amount)
                if position.exit_amount >= position.entry_amount * Dec(0.98):
                    position.status = "closed"
                    position.pnl = (position.exit_cost - position.entry_cost -
                                    position.fee)

            order.save()
            position.save()


def create_buy_orders(position, last_price):
    prices = []
    delta = last_price * Dec(hypnox.strategy.SPREAD)
    n_orders = hypnox.strategy.NUM_ORDERS

    init_price = last_price - delta
    prices = [init_price] + [delta / n_orders] * n_orders
    prices = [round(sum(prices[:i]), 2) for i in range(1, len(prices))]

    unit_cost = Dec(position.get_remaining_open() / n_orders)

    with hypnox.db.connection.atomic():
        for price in prices:
            amount = round(unit_cost / Dec(price), 8)
            logging.info("creating new buy order: " + position.symbol + " " +
                         str(amount) + " @ " + str(price) + " (" +
                         str(round(unit_cost, 2)) + ")")
            try:
                ex_order = exchange.create_order(position.symbol,
                                                 "LIMIT_MAKER", "buy", amount,
                                                 price)
            except ccxt.OrderImmediatelyFillable:
                continue

            try:
                ex_order["fee"] = (Dec(ex_order["fee"]["cost"]) *
                                   Dec(ex_order["price"]))
            except TypeError:
                ex_order["fee"] = 0

            hypnox.db.Order.create_from_ex_order(ex_order, position)


def create_sell_orders(position, last_price):
    prices = []
    delta = last_price * Dec(hypnox.strategy.SPREAD)
    n_orders = hypnox.strategy.NUM_ORDERS

    init_price = last_price + delta
    prices = [init_price] + [-delta / n_orders] * n_orders
    prices = [round(sum(prices[:i]), 2) for i in range(1, len(prices))]

    amount = round(
        Dec((position.entry_amount - position.exit_amount) / n_orders), 8)

    with hypnox.db.connection.atomic():
        for price in prices:
            logging.info("creating new sell order: " + position.symbol + " " +
                         str(amount) + " @ " + str(price) + " (" +
                         str(round(amount * price, 2)) + ")")
            try:
                ex_order = exchange.create_order(position.symbol,
                                                 "LIMIT_MAKER", "sell", amount,
                                                 price)
            except ccxt.OrderImmediatelyFillable:
                continue

            try:
                ex_order["fee"] = Dec(ex_order["fee"]["cost"])
            except TypeError:
                ex_order["fee"] = 0

            hypnox.db.Order.create_from_ex_order(ex_order, position)


def refresh(args):
    base = "BTC"
    quote = "USDT"
    symbol = base + quote

    now = datetime.datetime.utcnow()
    next_window = now + hypnox.strategy.WINDOW_SIZE

    ticker = exchange.fetch_ticker(symbol)
    last_price = Dec(ticker["last"])
    logging.info("last price is " + str(round(last_price, 2)))

    sync_orders(symbol)

    balance = exchange.fetch_balance()
    logging.info("balance is: " + str(round(balance[quote]["free"], 2)) + " " +
                 quote + " " + str("{:.8f}".format(balance[base]["free"])) +
                 " " + base)

    signal = hypnox.strategy.get_signal()
    try:
        position = hypnox.db.get_active_position(symbol).get()

        if now > position.next_window:
            logging.info("moving on to next window")
            position.next_window = next_window
            position.window_cost = 0
            position.save()

        if position.entry_cost > 0:
            curr_roi = (last_price * position.entry_amount /
                        position.entry_cost) - 1
            if (signal == "sell" or curr_roi >= hypnox.strategy.MINIMUM_ROI
                    or curr_roi <= hypnox.strategy.STOP_LOSS):
                logging.info("roi = " + str(round(curr_roi * 100, 2)) + "%")
                logging.info("closing position")
                position.status = "closing"
                position.save()
        elif position.entry_cost == 0 and position.status == "closing":
            logging.info("entry_cost is 0, closing position")
            position.status = "closed"
            position.save()

        if position.status == "opening":
            if (datetime.datetime.utcnow() < position.next_window
                    and position.get_remaining_open() <= 1):
                logging.info("window is full, skipping...")
                return

            create_buy_orders(position, last_price)
        elif position.status == "closing":
            if (datetime.datetime.utcnow() < position.next_window
                    and position.get_remaining_close() <= 1):
                logging.info("window is full, skipping...")
                return

            create_sell_orders(position, last_price)
        else:
            logging.info("position is " + position.status +
                         ", skipping order creation...")
    except peewee.DoesNotExist:
        logging.info("no active position")
        if signal == "buy":
            window_max = round(
                balance[quote]["free"] / hypnox.strategy.NUM_ORDERS, 2)
            logging.info("opening position")
            position = hypnox.db.Position(symbol=symbol,
                                          next_window=next_window,
                                          window_max=window_max,
                                          window_cost=0,
                                          status="opening",
                                          target_cost=(balance[quote]["free"] *
                                                       0.98))
            position.save()
            create_buy_orders(position, last_price)
