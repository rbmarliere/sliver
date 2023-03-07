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
    if exception:
        msg = "{m}: {e}".format(m=msg, e=exception)
        get_logger("exception", suppress_output=True) \
            .exception(exception, exc_info=True)

    log.error(msg)

    if log.name == "watchdog" or log.name == "stream":
        msg = "{l}: {m}".format(l=log.name, m=msg)
        send_telegram(msg)


def warning(msg):
    log.warning(msg)

    if log.name == "watchdog" or log.name == "stream":
        msg = "{l}: {m}".format(l=log.name, m=msg)
        send_telegram(msg)


def notice(user, msg):
    send_user_telegram(user, msg)


def disable(locals):
    if "position" in locals:
        position = locals["position"]
        user_strat = position.user_strategy
    if "user_strat" in locals:
        user_strat.disable()


def postpone(locals):
    if "position" in locals():
        position = locals["position"]
        if position.status != "open":
            position.postpone(interval_in_minutes=5)
    if "strategy" in locals():
        strategy = locals["strategy"]
        strategy.postpone(interval_in_minutes=5)


def watch():
    set_logger("watchdog")

    while (True):
        try:
            core.db.connection.connect()

            # TODO risk assessment:
            # - red flag -- exit all positions
            # - yellow flag -- new buy signals ignored & reduce curr. positions
            # - green flag -- all signals are respected
            # in general, account for overall market risk and volatility
            # maybe use GARCH to model volatility, or a machine learning model
            # maybe user.max_risk and user.max_volatility

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

            time.sleep(int(core.config["WATCHDOG_INTERVAL"]))

        except (core.db.Credential.DoesNotExist,
                ccxt.AuthenticationError,
                ccxt.InsufficientFunds) as e:
            error(e.__class__.__name__, e)
            disable(locals())

        except (ccxt.RateLimitExceeded,
                ccxt.OnMaintenance,
                ccxt.RequestTimeout) as e:
            error(e.__class__.__name__, e)
            postpone(locals())

        except (ccxt.NetworkError,
                ccxt.ExchangeError,
                core.errors.ModelTooLarge,
                core.errors.ModelDoesNotExist) as e:
            error(e.__class__.__name__, e)
            if "strategy" in locals():
                strategy.disable()

        except peewee.OperationalError as e:
            error("database error", e)
            time.sleep(10)

        except Exception as e:
            error("crashed", e)
            break

        except KeyboardInterrupt:
            break

        finally:
            core.db.connection.close()
            if "position" in locals():
                del position
            if "strategy" in locals():
                del strategy
            if "user_strat" in locals():
                del user_strat
