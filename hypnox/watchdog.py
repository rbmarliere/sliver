import datetime
import logging
import logging.handlers
import time

import ccxt
import peewee

import hypnox


def get_logger(name, suppress_output=False):
    log_file = hypnox.utils.get_abs_path("/../log/" + name + ".log")

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


log = get_logger("hypnox")
stream_log = get_logger("stream")
script_log = get_logger("script")
exception_log = get_logger("exception", suppress_output=True)


def watch(args):
    global log
    log = get_logger("watchdog")

    hypnox.telegram.notify("watchdog init")
    log.info("watchdog init")
    while (True):
        try:
            hypnox.db.connection.connect(reuse_if_open=True)

            # kill switch if no active strategies
            first_active_strat = hypnox.db.get_active_strategies().first()
            assert first_active_strat is not None

            strategies = [s for s in hypnox.db.get_pending_strategies()]

            # if no pending strategies, sleep until next demand
            if len(strategies) == 0:
                next_refresh = first_active_strat.next_refresh
                delta = int((next_refresh -
                             datetime.datetime.utcnow()).total_seconds()) + 5
                if delta > 0:
                    log.info("----------------------------------------------")
                    log.info("next refresh at " + str(next_refresh) +
                             " for strategy " + str(first_active_strat.id))
                    log.info("sleeping for " + str(delta) + " seconds")
                    time.sleep(delta)

            # refresh each strategy
            for strategy in strategies:
                # don't refresh strategy if it doesn't need to
                if datetime.datetime.utcnow() < strategy.next_refresh:
                    continue

                log.info("==============================================")
                log.info("refreshing strategy " + str(strategy.id))
                log.info("market is " + strategy.market.symbol)
                log.info("timeframe is " + strategy.timeframe)

                for user in strategy.get_active_users():
                    user_strat = user.userstrategy_set.get()

                    log.info("refreshing " + user.name + "'s strategy " +
                             str(user_strat.id))

                    credential = user.get_credential_by_exchange(
                        strategy.market.exchange)
                    hypnox.exchange.set_api(credential)

                    # check if exchange is alive
                    latency = hypnox.exchange.get_latency()
                    if latency > 1300:
                        raise ccxt.NetworkError

                    hypnox.exchange.download(strategy.market,
                                             strategy.timeframe)

                    # get current position for given user_strategy
                    position = user_strat.get_active_position()

                    hypnox.exchange.sync_orders(position)

                    hypnox.inventory.sync_balances(user, strategy.market)

                    # inventory.sync_balance ? (against "strategy inventory")
                    # if insufficient funds position --> stalled status?
                    # hypnox.inventory.sync()
                    # check trades, pnl, balances, risk

                    hypnox.exchange.refresh(user_strat)

                    # update current strategy next refresh time
                    strategy.next_refresh = (
                        datetime.datetime.utcnow() +
                        datetime.timedelta(minutes=strategy.refresh_interval))
                    strategy.save()

        except ccxt.RateLimitExceeded:
            sleep_time = strategy.market.exchange.rate_limit
            log.info("rate limit exceeded, sleeping for " + str(sleep_time) +
                     " seconds")
            time.sleep(sleep_time)

        except ccxt.AuthenticationError:
            log.error("authentication error, disabling user's strategy")
            user_strat.active = False
            user_strat.save()

        except ccxt.InsufficientFunds:
            log.error("insufficient funds, disabling user's strategy")
            user_strat.active = False
            user_strat.save()

        except ccxt.NetworkError:
            log.warning("exchange api error, "
                        "sleeping 60 seconds before trying again...")
            time.sleep(60)

        except peewee.OperationalError:
            log.error("can't connect to database!")
            break

        except KeyboardInterrupt:
            log.info("got keyboard interrupt")
            break

        except Exception as e:
            hypnox.telegram.notify("got exception: " + str(e))
            log.error(e)
            exception_log.exception(e, exc_info=True)
            break

    hypnox.telegram.notify("shutting down...")
    log.warning("shutting down...")
