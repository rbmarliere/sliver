import datetime
import logging
import time

import ccxt
import pandas
import peewee

import src as hypnox

# https://docs.ccxt.com/en/latest/manual.html?#exception-hierarchy

exchange_id = "binance"
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    "apiKey": hypnox.config.config["BINANCE_KEY"],
    "secret": hypnox.config.config["BINANCE_SECRET"],
})


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
            logging.warning("rate limit exceeded, sleeping for " +
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
