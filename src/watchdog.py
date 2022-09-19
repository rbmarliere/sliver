import logging
import os
import time

import src as hypnox

log_file = os.path.abspath(__file__) + "/../../log/hypnox.log"

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s:%(funcName)s -- %(message)s")

file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

log = logging.getLogger("hypnox")
log.setLevel(logging.INFO)
log.addHandler(file_handler)
log.addHandler(stream_handler)


def check_log():
    print("check_log")
    # with open(log_file, "r") as f:
    #     re.search("ERROR", f)
    #     re.search("CRITICAL", f)


def watch(args):
    strategy = hypnox.config.StrategyConfig(args.strategy).config
    while (True):
        try:
            sleep_in_secs = strategy["REFRESH_TIMEDELTA_IN_MINUTES"] * 60
            log.info("sleeping for " + str(sleep_in_secs) + " seconds...")
            time.sleep(sleep_in_secs)

            hypnox.exchange.check_api()  # latency etc
            check_log()

            hypnox.inventory.sync()
            check_log()

            args.since = "20220101"
            args.symbol = strategy["SYMBOL"]
            args.timeframe = strategy["TIMEFRAME"]
            hypnox.exchange.download(args)
            check_log()

            args.model = strategy["I_MODEL"]
            hypnox.db.replay(args)
            check_log()

            # args.model = strategy["P_MODEL"]
            # hypnox.db.replay(args)
            # check_log()

            hypnox.exchange.refresh(args)
            check_log()

        except Exception as e:
            # hypnox.telegram.notify()
            log.exception(e, exc_info=True)
            break
