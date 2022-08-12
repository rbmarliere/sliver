import datetime
import logging
import time

import ccxt

import src as hypnox

exchange_id = "binance"
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    "apiKey": hypnox.config.config["BINANCE_KEY"],
    "secret": hypnox.config.config["BINANCE_SECRET"],
})


def download(args):
    sleep_time = (exchange.rateLimit / 1000) + 1
    page_size = 500
    page_start = int(datetime.datetime(2020, 6, 1).timestamp() * 1000)

    prices = []
    while True:
        try:
            logging.info("downloading from " + str(page_start))
            page = exchange.fetch_ohlcv("BTC/USDT",
                                        since=page_start,
                                        timeframe="4h",
                                        limit=page_size)
            prices += list(
                map(
                    lambda x: [
                        datetime.datetime.utcfromtimestamp(x[0] / 1000), x[1],
                        x[2], x[3], x[4], x[5]
                    ], page))
            if len(page) < page_size:
                break
            page_start = page[-1][0] + 4 * 60 * 60 * 1000
        except ccxt.RateLimitExceeded:
            logging.warning("rate limit exceeded, sleeping for " +
                            str(sleep_time) + " seconds")
            time.sleep(sleep_time)
            continue
        # TODO: better error handling
        # https://docs.ccxt.com/en/latest/manual.html?#exception-hierarchy

    with hypnox.db.connection.atomic():
        hypnox.db.Price.create_table()
        hypnox.db.Price.insert_many(
            prices,
            fields=[
                hypnox.db.Price.time, hypnox.db.Price.open,
                hypnox.db.Price.high, hypnox.db.Price.low,
                hypnox.db.Price.close, hypnox.db.Price.volume
            ]).execute()
