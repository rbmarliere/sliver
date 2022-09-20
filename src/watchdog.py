import logging
import logging.handlers
import os
import re
import time

import src as hypnox


def get_log_file(name):
    return os.path.abspath(
        os.path.dirname(os.path.abspath(__file__)) + "/../log/" + name +
        ".log")


def get_logger(name):
    log_file = get_log_file(name)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s -- %(message)s :: %(filename)s@%(funcName)s"
    )

    file_handler = logging.handlers.RotatingFileHandler(log_file,
                                               maxBytes=52,
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


def check_log(log_file):
    with open(log_file, "r") as f:
        match = re.findall("ERROR|CRITICAL|Exception", f.read())
        if match:
            raise Exception("found error in log " + log_file)


def watch(args):
    strategy = hypnox.config.StrategyConfig(args.strategy).config

    global log
    log = get_logger("watchdog")
    log_file = get_log_file("watchdog")

    log.info("watchdog init")
    while (True):
        try:
            sleep_in_secs = strategy["REFRESH_TIMEDELTA_IN_MINUTES"] * 60
            log.info("sleeping for " + str(sleep_in_secs) + " seconds...")
            time.sleep(sleep_in_secs)

            hypnox.exchange.check_api()  # latency etc
            check_log(log_file)

            hypnox.exchange.sync_orders(strategy["SYMBOL"])
            # inventory.sync_balance ? (against "strategy inventory")
            # if insufficient funds position --> stalled status?
            check_log(log_file)

            hypnox.inventory.sync()
            # check trades, pnl, balances, risk
            check_log(log_file)

            args.since = "20220101"
            args.symbol = strategy["SYMBOL"]
            args.timeframe = strategy["TIMEFRAME"]
            hypnox.exchange.download(args)
            check_log(log_file)

            args.model = strategy["I_MODEL"]
            hypnox.db.replay(args)
            check_log(log_file)

            # args.model = strategy["P_MODEL"]
            # hypnox.db.replay(args)
            # check_log(log_file)

            hypnox.exchange.refresh(args)
            check_log(log_file)

        except Exception as e:
            # hypnox.telegram.notify()
            log.exception(e, exc_info=True)
            break
        except KeyboardInterrupt:
            log.info("got keyboard interrupt")
            break

    log.info("shutting down...")
