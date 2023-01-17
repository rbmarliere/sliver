import logging.handlers
import time

import ccxt
import peewee
import telegram

import core


def send_user_telegram(user, msg):
    while True:
        try:
            assert core.config["TELEGRAM_KEY"]
            assert user.telegram_username

            bot = telegram.Bot(core.config["TELEGRAM_KEY"])

            if user.telegram_chat_id is None:
                updates = bot.get_updates()
                for update in updates:
                    if update.message.chat.username == user.telegram_username:
                        user.telegram_chat_id = update.message.chat.id
                        user.save()

            bot.send_message(text=msg,
                             chat_id=user.telegram_chat_id)

        except (KeyError, AssertionError):
            pass

        except telegram.error.NetworkError:
            time.sleep(30)
            continue

        break


def send_telegram(message):
    while True:
        try:
            assert core.config["TELEGRAM_KEY"]
            assert core.config["TELEGRAM_CHANNEL"]

            bot = telegram.Bot(core.config["TELEGRAM_KEY"])

            bot.send_message(text=message,
                             chat_id=core.config["TELEGRAM_CHANNEL"])

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


def warning(msg):
    log.warning(msg)

    if log.name == "watchdog" or log.name == "stream":
        msg = "{l}: {m}".format(l=log.name, m=msg)
        send_telegram(msg)


def notice(user, msg):
    log.info(msg)

    if log.name == "watchdog" or log.name == "stream":
        msg = "{l}: {m}".format(l=log.name, m=msg)
        send_user_telegram(user, msg)


def watch():
    set_logger("watchdog")
    warning("init")

    while (True):
        core.db.connection.connect()

        try:
            for position in core.db.get_opening_positions():
                stopped = position.check_stops()
                if stopped:
                    position.refresh()

            for strategy in core.db.get_pending_strategies():
                strategy.refresh()

                for user_strat in strategy.get_active_users():
                    user_strat.refresh()

            for position in core.db.get_pending_positions():
                position.refresh()

            time.sleep(10)

        except core.db.Credential.DoesNotExist as e:
            error("credential not found", e)
            if "user_strat" in locals():
                user_strat.disable()

        except ccxt.AuthenticationError as e:
            error("authentication error", e)
            if "user_strat" in locals():
                user_strat.disable()

        except ccxt.InsufficientFunds as e:
            error("insufficient funds", e)
            if "user_strat" in locals():
                user_strat.disable()

        except (core.errors.ModelTooLarge,
                core.errors.ModelDoesNotExist):
            if "strategy" in locals():
                strategy.disable()

        except ccxt.RateLimitExceeded as e:
            error("rate limit exceeded", e)
            # TODO check flow

        except ccxt.ExchangeError as e:
            error("exchange error", e)
            if "strategy" in locals():
                strategy.disable()
            if "user_strat" in locals():
                user_strat.disable()

        except ccxt.NetworkError as e:
            error("exchange api error", e)
            # strategy.postpone()

        except peewee.OperationalError as e:
            error("database error", e)
            time.sleep(60)

        except KeyboardInterrupt:
            info("got keyboard interrupt")
            break

        except Exception as e:
            error("crashed", e)
            break

        core.db.connection.close()

    warning("shutdown")
