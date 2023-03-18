import logging.handlers
import time

import core


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
        core.alert.send_message(msg)


def warning(msg):
    log.warning(msg)

    if log.name == "watchdog" or log.name == "stream":
        msg = "{l}: {m}".format(l=log.name, m=msg)
        core.alert.send_message(msg)


def notice(user, msg):
    core.alert.send_user_message(user, msg)


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

        except Exception as e:
            error(e.__class__.__name__, e)
            if "user_strat" in locals():
                user_strat.disable()
            if "strategy" in locals():
                strategy.disable()

        except (core.errors.BaseError,
                core.errors.ModelTooLarge,
                core.errors.ModelDoesNotExist) as e:
            error(e.__class__.__name__, e)
            if "strategy" in locals():
                strategy.disable()

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
