import datetime
import logging
import logging.handlers
import time

import ccxt
import peewee

import hypnox


def get_logger(name, suppress_output=False):
    log_file = hypnox.config["HYPNOX_LOGS_DIR"] + "/" + name + ".log"

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
            assert first_active_strat

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
                    continue

            # refresh each strategy
            for strategy in strategies:
                # don't refresh strategy if it doesn't need to
                if datetime.datetime.utcnow() < strategy.next_refresh:
                    continue

                symbol = strategy.market.get_symbol()

                log.info("==============================================")
                log.info("refreshing strategy " + str(strategy.id))
                log.info("market is " + symbol)
                log.info("timeframe is " + strategy.timeframe)

                hypnox.strategy.refresh(strategy)

                users = [u for u in strategy.get_active_users()]
                i = 0

                while True:
                    try:
                        u_strat = users[i]

                        log.info(
                            "..............................................")
                        log.info("refreshing " + u_strat.user.name +
                                 "'s strategy " + str(u_strat.id))

                        # set api to current exchange
                        credential = u_strat.user.get_credential_by_exchange(
                            strategy.market.base.exchange)
                        hypnox.exchange.set_api(credential)

                        p = hypnox.exchange.api.fetch_ticker(symbol)
                        last_price = strategy.market.quote.transform(p["last"])
                        hypnox.watchdog.log.info("last " + symbol +
                                                 " price is $" +
                                                 str(p["last"]))

                        # get active position for current user_strategy
                        position = u_strat.get_active_position_or_none()

                        if position:
                            hypnox.exchange.sync_orders(position)

                        # sync user's balances across all exchanges
                        hypnox.inventory.sync_balances(u_strat.user)

                        # download historical price ohlcv data
                        hypnox.exchange.download(strategy.market,
                                                 strategy.timeframe)

                        if position is None:
                            hypnox.watchdog.log.info("no active position")

                            # create position if apt
                            if strategy.signal == "buy":
                                t_cost = hypnox.inventory.get_target_cost(
                                    u_strat)

                                position = hypnox.db.Position.open(
                                    u_strat, t_cost)

                                hypnox.telegram.notify(
                                    "opened position for user " +
                                    u_strat.user.name + " under strategy " +
                                    u_strat.strategy.id + " (" +
                                    u_strat.strategy.description +
                                    ") in market " +
                                    u_strat.strategy.market.get_symbol())

                        if position:
                            hypnox.exchange.refresh(position, strategy.signal,
                                                    last_price)

                        i += 1

                    except IndexError:
                        break

                    except ccxt.AuthenticationError:
                        log.error(
                            "authentication error, disabling user's strategy")
                        u_strat.active = False
                        u_strat.save()
                        i += 1

                    except ccxt.InsufficientFunds:
                        log.error(
                            "insufficient funds, disabling user's strategy")
                        u_strat.active = False
                        u_strat.save()
                        i += 1

                    except ccxt.RateLimitExceeded:
                        sleep_time = strategy.market.base.exchange.rate_limit
                        log.info("rate limit exceeded, sleeping for " +
                                 str(sleep_time) + " seconds")
                        time.sleep(sleep_time)

                    except ccxt.NetworkError:
                        log.info("exchange api error, "
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
    log.info("shutting down...")
