import datetime
import logging
import logging.handlers
import time

import ccxt
import peewee

import core


def get_logger(name, suppress_output=False):
    log_file = core.config["HYPNOX_LOGS_DIR"] + "/" + name + ".log"

    formatter = logging.Formatter("")

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


def watch():
    set_logger("watchdog")

    core.telegram.notify("watchdog init")
    log.info("watchdog init")

    model_i = core.models.load(core.config["HYPNOX_DEFAULT_MODEL_I"])
    model_p = core.models.load(core.config["HYPNOX_DEFAULT_MODEL_P"])

    n_tries = 0

    while (True):
        try:
            core.db.connection.connect(reuse_if_open=True)

            # kill switch if no active strategies
            first_active_strat = core.db.get_active_strategies().first()
            assert first_active_strat

            strategies = [s for s in core.db.get_pending_strategies()]

            # if no pending strategies, sleep until next demand
            if len(strategies) == 0:
                next_refresh = first_active_strat.next_refresh
                delta = int((next_refresh -
                             datetime.datetime.utcnow()).total_seconds())
                if delta > 0:
                    log.info("--------------------------------------------\n"
                             "next refresh at {r} "
                             "for strategy {s} \n"
                             "sleeping for {t} seconds"
                             .format(r=next_refresh,
                                     s=first_active_strat,
                                     t=delta))
                    time.sleep(delta)
                    continue

            # refresh each strategy
            for strategy in strategies:
                now = datetime.datetime.utcnow()

                # don't refresh strategy if it doesn't need to
                if now < strategy.next_refresh:
                    continue

                symbol = strategy.market.get_symbol()

                log.info("============================================\n"
                         "refreshing strategy {s} \n"
                         "market is {m} \n"
                         "timeframe is {T} \n"
                         "exchange is {e}"
                         .format(s=strategy,
                                 m=symbol,
                                 T=strategy.timeframe,
                                 e=strategy.market.base.exchange.name))

                core.exchange.set_api(exchange=strategy.market.base.exchange)

                # update tweet scores
                core.models.replay(model_i)
                core.models.replay(model_p)

                # download historical price ohlcv data
                core.exchange.download(strategy.market,
                                       strategy.timeframe)

                # refresh strategy params
                core.strategy.refresh(strategy, next=now)

                users = [u for u in strategy.get_active_users()]

                if len(users) == 0:
                    log.info("no active users found, skipping...")
                    continue

                i = 0
                while True:
                    try:
                        u_strat = users[i]

                        log.info(
                            "............................................\n"
                            "refreshing {u}'s strategy {s}"
                            .format(u=u_strat.user.email,
                                    s=u_strat))

                        # set api to current exchange
                        credential = (u_strat
                                      .user
                                      .get_credential_by_exchange_or_none(
                                          strategy.market.base.exchange))
                        if credential is None:
                            core.watchdog.log.info("credential not found, "
                                                   "skipping user...")
                            continue
                        core.exchange.set_api(cred=credential)

                        p = core.exchange.api.fetch_ticker(symbol)
                        last_price = strategy.market.quote.transform(p["last"])
                        core.watchdog.log.info("last {m} price is ${p}"
                                               .format(m=symbol,
                                                       p=p["last"]))

                        # get active position for current user_strategy
                        position = u_strat.get_active_position_or_none()

                        if position:
                            position = core.exchange.sync_orders(position)

                        # sync user's balances across all exchanges
                        core.inventory.sync_balances(u_strat.user)

                        if position is None:
                            core.watchdog.log.info("no active position")

                            # create position if apt
                            if strategy.signal == "buy":
                                t_cost = core.inventory.get_target_cost(
                                    u_strat)

                                if t_cost > 0:
                                    position = core.db.Position.open(
                                        u_strat, t_cost)

                                    core.telegram.notify(
                                        "watchdog: "
                                        "opened position for user {u} "
                                        "under strategy {s} "
                                        "in market {m} "
                                        "with target cost {c} "
                                        .format(
                                            u=u_strat.user.email,
                                            s=u_strat.strategy,
                                            m=u_strat.strategy
                                            .market.get_symbol(),
                                            c=u_strat.strategy
                                            .market.quote.print(t_cost)))

                        if position:
                            core.exchange.refresh(position, strategy.signal,
                                                  last_price)

                        i += 1

                    except IndexError:
                        break

                    except ccxt.AuthenticationError:
                        log.error("authentication error, "
                                  "disabling user's strategy...")
                        u_strat.active = False
                        u_strat.save()
                        i += 1

                    except ccxt.InsufficientFunds:
                        log.error("insufficient funds, "
                                  "disabling user's strategy...")
                        u_strat.active = False
                        u_strat.save()
                        i += 1

                    except core.db.Credential.DoesNotExist:
                        log.info("user has no credential for this exchange, "
                                 "disabling user's strategy...")
                        u_strat.active = False
                        u_strat.save()
                        i += 1

                    except ccxt.RateLimitExceeded:
                        log.info("rate limit exceeded, "
                                 "skipping user...")

        except ccxt.ExchangeError:
            log.info("exchange error, "
                     "disabling strategy...")
            strategy.active = False
            strategy.save()

        except ccxt.NetworkError:
            log.info("exchange api error")
            n_tries += 1
            if n_tries > 9:
                n_tries = 0
                core.telegram.notify("watchdog: exchange api error, "
                                     "disabling strategy {s}"
                                     .format(s=strategy))

        except peewee.OperationalError:
            log.error("can't connect to database!")
            break

        except KeyboardInterrupt:
            log.info("got keyboard interrupt")
            break

        except Exception as e:
            core.telegram.notify("watchdog crashed!")
            log.error(e)
            exception_log = get_logger("exception", suppress_output=True)
            exception_log.exception(e, exc_info=True)
            break

    core.telegram.notify("watchdog shutting down")
    log.info("shutting down...")
