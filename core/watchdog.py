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
    send_user_telegram(user, msg)


def watch():
    # TODO refactor error handling
    set_logger("watchdog")
    warning("init")

    while (True):
        core.db.connection.connect()

        try:
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

        except core.db.Credential.DoesNotExist as e:
            error("credential not found", e)
            if "position" in locals():
                user_strat = position.user_strategy
            if "user_strat" in locals():
                user_strat.disable()

        except ccxt.AuthenticationError as e:
            error("authentication error", e)
            if "position" in locals():
                user_strat = position.user_strategy
            if "user_strat" in locals():
                user_strat.disable()

        except ccxt.InsufficientFunds as e:
            error("insufficient funds", e)
            if "position" in locals():
                user_strat = position.user_strategy
            if "user_strat" in locals():
                user_strat.disable()

        except (core.errors.ModelTooLarge,
                core.errors.ModelDoesNotExist):
            if "strategy" in locals():
                strategy.disable()

        except ccxt.RateLimitExceeded as e:
            error("rate limit exceeded", e)
            if "position" in locals():
                # TODO postpone if status != open
                position.postpone(interval_in_minutes=5)
            if "strategy" in locals():
                strategy.postpone(interval_in_minutes=5)

        except ccxt.OnMaintenance as e:
            error("exchange in maintenance", e)
            if "position" in locals():
                position.postpone(interval_in_minutes=5)

        except ccxt.ExchangeError as e:
            error("exchange error", e)
            if "strategy" in locals():
                strategy.disable()
            if "position" in locals():
                user_strat = position.user_strategy
            if "user_strat" in locals():
                user_strat.disable()

        except ccxt.NetworkError as e:
            error("exchange api error", e)
            if "position" in locals():
                position.postpone(interval_in_minutes=5)
            if "strategy" in locals():
                strategy.postpone(interval_in_minutes=5)

        except peewee.OperationalError as e:
            error("database error", e)
            time.sleep(10)

        except KeyboardInterrupt:
            info("got keyboard interrupt")
            break

        except Exception as e:
            error("crashed", e)
            break

        finally:
            if "position" in locals():
                del position
            if "strategy" in locals():
                del strategy
            if "user_strat" in locals():
                del user_strat

        core.db.connection.close()

    warning("shutdown")
