import logging.handlers
import time

import ccxt
import peewee
import telegram

import core


def send_telegram(message):
    while True:
        try:
            assert core.config["TELEGRAM_KEY"]
            assert core.config["TELEGRAM_CHANNEL"]
            bot = telegram.Bot(core.config["TELEGRAM_KEY"])
            bot.send_message(text=message,
                             chat_id=core.config["TELEGRAM_CHANNEL"])

            # TODO: send to user
        except (KeyError, AssertionError):
            pass
        except telegram.error.NetworkError:
            time.sleep(30)
            continue
        break


def get_logger(name, suppress_output=False):
    log_file = core.config["LOGS_DIR"] + "/" + name + ".log"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s -- %(message)s")

    formatter.converter = time.gmtime

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=52428800,  # 50mb
        backupCount=32)
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


log = get_logger("core")


def info(msg):
    log.info(msg)


def error(msg, exception):
    log.error(msg)

    if exception:
        get_logger("exception", suppress_output=True) \
            .exception(exception, exc_info=True)

    if log.name == "watchdog" or log.name == "stream":
        msg = "{l}: {m}".format(l=log.name, m=msg)
        send_telegram(msg)


def notice(msg):
    log.info(msg)

    if log.name == "watchdog" or log.name == "stream":
        msg = "{l}: {m}".format(l=log.name, m=msg)
        send_telegram(msg)


def watch():
    set_logger("watchdog")
    notice("init")

    while (True):
        try:
            core.db.connection.connect()

            # for position in core.db.get_active_positions():
            # TODO check SL/SG

            for strategy in core.db.get_pending_strategies():
                # download price data, update indicators and signal
                strategy.refresh()

                for user_strat in strategy.get_active_users():
                    try:
                        # sync orders and balances, update or create position
                        user_strat.refresh()

                    except core.db.Credential.DoesNotExist as e:
                        error("credential not found", e)
                        user_strat.disable()

                    except ccxt.AuthenticationError as e:
                        error("authentication error", e)
                        user_strat.disable()

                    except ccxt.InsufficientFunds as e:
                        error("insufficient funds", e)
                        user_strat.disable()

                    except ccxt.RateLimitExceeded as e:
                        error("rate limit exceeded, skipping user...", e)

                    except ccxt.ExchangeError as e:
                        error("exchange error", e)
                        user_strat.disable()

                    except ccxt.NetworkError as e:
                        error("exchange api error, skipping user...", e)

            time.sleep(60)

        except (core.errors.ModelTooLarge,
                core.errors.ModelDoesNotExist):
            strategy.disable()

        except ccxt.ExchangeError as e:
            error("exchange error", e)
            strategy.disable()

        except ccxt.NetworkError as e:
            error("exchange api error", e)
            strategy.postpone()

        except peewee.OperationalError as e:
            error("database error", e)
            time.sleep(60)

        except KeyboardInterrupt:
            info("got keyboard interrupt")
            break

        except Exception as e:
            error("crashed", e)
            break

        finally:
            core.db.connection.close()

    notice("shutdown")
