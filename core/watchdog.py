import logging
import logging.handlers
import time

import ccxt
import peewee
import tensorflow

import core


def get_logger(name, suppress_output=False):
    log_file = core.config["HYPNOX_LOGS_DIR"] + "/" + name + ".log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s -- %(message)s :: "
        "%(funcName)s@%(filename)s:%(lineno)d")

    formatter.converter = time.gmtime

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=52428800,  # 50mb
        backupCount=10)
    file_handler.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    log.addHandler(file_handler)

    if not suppress_output:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)

    return log


def set_logger(name):
    global log
    log = get_logger(name)


log = get_logger("hypnox")


def info(msg):
    log.info(msg)


def error(msg, e):
    log.error(msg)
    get_logger("exception", suppress_output=True) \
        .exception(e, exc_info=True)
    core.telegram.notice(msg)


def notice(msg):
    msg = "{l}: {m}".format(l=log.name, m=msg)
    log.info(msg)
    core.telegram.notice(msg)


def watch():
    set_logger("watchdog")
    notice("init")

    n_tries = 0

    while (True):
        try:
            core.db.connection.connect(reuse_if_open=True)

            for strategy in core.db.get_pending_strategies():
                core.strategy.refresh(strategy)

                for user_strat in strategy.get_active_users():
                    core.strategy.refresh_user(user_strat)

            first_active_strat = core.db.get_active_strategies().first()
            next_refresh = first_active_strat.next_refresh
            info("-------------------------------------------")
            info("next refresh at {r} for strategy {s}"
                 .format(r=next_refresh,
                         s=first_active_strat))

            time.sleep(60)

        except ccxt.AuthenticationError as e:
            error("authentication error", e)
            user_strat.disable()

        except ccxt.InsufficientFunds as e:
            error("insufficient funds", e)
            user_strat.disable()

        except core.db.Credential.DoesNotExist as e:
            error("credential not found", e)
            user_strat.disable()

        except ccxt.RateLimitExceeded as e:
            error("rate limit exceeded, skipping user...", e)

        except core.errors.ModelDoesNotExist as e:
            error("can't load model", e)
            strategy.disable()

        except tensorflow.errors.ResourceExhaustedError as e:
            error("can't load model", e)
            strategy.disable()

        except ccxt.ExchangeError as e:
            error("exchange error", e)
            strategy.disable()

        except ccxt.NetworkError as e:
            error("exchange api error", e)
            n_tries += 1
            if n_tries > 9:
                n_tries = 0
                notice("exchange api error, disabling user's strategy {s}"
                       .format(s=user_strat))
                user_strat.disable()

        except peewee.OperationalError as e:
            error("can't connect to database!", e)
            break

        except KeyboardInterrupt:
            info("got keyboard interrupt")
            break

        except Exception as e:
            error("watchdog crashed", e)
            break

    notice("shutdown")
