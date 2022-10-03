import logging
import logging.handlers
import os
import time

import ccxt

import src as hypnox


def get_logger(name):
    log_file = os.path.abspath(
        os.path.dirname(os.path.abspath(__file__)) + "/../log/" + name +
        ".log")

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s -- %(message)s :: "
        "%(funcName)s@%(filename)s:%(lineno)d")

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=52428800,  # 50mb
        backupCount=10)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    log.addHandler(file_handler)
    log.addHandler(stream_handler)

    return log


log = get_logger("hypnox")
stream_log = get_logger("stream")
scripts_log = get_logger("scripts")


def watch(args):
    strategy = hypnox.utils.load_json("/../etc/strategies/" + args.strategy +
                                      ".json")

    global log
    log = get_logger("watchdog")

    hypnox.telegram.notify("watchdog init")
    log.info("watchdog init")
    while (True):
        try:
            market = hypnox.db.get_market(hypnox.exchange.api.id,
                                          strategy["SYMBOL"])

            hypnox.exchange.check_api()

            # cancel all orders outside sync_orders ?
            hypnox.exchange.sync_orders(market)
            # inventory.sync_balance ? (against "strategy inventory")
            # if insufficient funds position --> stalled status?

            hypnox.inventory.sync()
            # check trades, pnl, balances, risk

            args.symbol = strategy["SYMBOL"]
            args.timeframe = strategy["TIMEFRAME"]
            hypnox.exchange.download(args)

            # args.model = strategy["I_MODEL"]
            # hypnox.db.replay(args)

            # args.model = strategy["P_MODEL"]
            # hypnox.db.replay(args)

            hypnox.exchange.refresh(args)

            sleep_in_secs = strategy["REFRESH_TIMEDELTA_IN_MINUTES"] * 60
            log.info("sleeping for " + str(sleep_in_secs) + " seconds...")
            time.sleep(sleep_in_secs)

        except ccxt.NetworkError:
            log.warning("exchange api is unreachable! "
                        "sleeping 60 seconds before trying again...")
            time.sleep(60)

        except KeyboardInterrupt:
            log.info("got keyboard interrupt")
            break

        except Exception as e:
            hypnox.telegram.notify("got exception: " + str(e))
            log.exception(e, exc_info=True)
            break

    hypnox.telegram.notify("shutting down...")
    log.info("shutting down...")
