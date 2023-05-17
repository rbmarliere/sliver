import logging
import logging.config
import multiprocessing
import os
import time

import sliver.database as db
from sliver.alert import send_message
from sliver.config import Config
from sliver.exceptions import (
    BaseError,
    DisablingError,
    PostponingError,
)
from sliver.position import Position
from sliver.strategies.status import StrategyStatus
from sliver.strategy import BaseStrategy


def get_file_handler(filename, filepath=None):
    path = (
        f"{Config().LOGS_DIR}/{filepath}" if filepath is not None else Config().LOGS_DIR
    )

    os.makedirs(path, exist_ok=True)

    log_file = f"{path}/{filename}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=52428800, backupCount=32  # 50mb
    )

    return file_handler


class Watchdog:
    def __init__(self, num_workers=None):
        self.num_workers = num_workers if num_workers is not None else 1
        self.proc_queue = multiprocessing.Queue()
        self.log_queue = multiprocessing.Queue()

    def run(self):
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": True,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s -- %(message)s",
                        "datefmt": "%Y-%m-%d %H:%M:%S",
                        "converter": time.gmtime,
                    }
                },
                "filters": {
                    "stdout": {
                        "()": StdoutFilter,
                        "level": "WARNING",
                    },
                },
                "handlers": {
                    "stdout": {
                        "class": "logging.StreamHandler",
                        "level": "INFO",
                        "formatter": "default",
                        "filters": ["stdout"],
                    },
                    "stderr": {
                        "()": get_file_handler,
                        "level": "ERROR",
                        "filename": "errors",
                        "formatter": "default",
                    },
                    "file": {
                        "()": get_file_handler,
                        "level": "INFO",
                        "filename": "watchdog",
                        "formatter": "default",
                    },
                },
                "root": {"handlers": ["stdout", "stderr", "file"], "level": "INFO"},
            }
        )

        if self.num_workers > 1:
            for handler in logging.getLogger().handlers:
                handler.formatter = None
            logging.handlers.QueueListener(self.log_queue, LogHandler()).start()
            for w in range(self.num_workers):
                p = Worker(self.proc_queue, self.log_queue)
                p.start()

        db.init()
        BaseStrategy.stop_all()
        Position.stop_all()

        while True:
            try:
                self.refresh_opening_positions()
                self.refresh_idle_strategies()
                self.refresh_waiting_strategies()
                self.refresh_pending_positions()

                time.sleep(int(Config().WATCHDOG_INTERVAL))

            except KeyboardInterrupt:
                break

    def refresh_opening_positions(self):
        for position in Position.get_opening():
            t = Task(position, call="check_stops")
            if self.num_workers == 1:
                t.run()
            else:
                self.proc_queue.put(t)

    def refresh_idle_strategies(self):
        markets = {}
        for base_st in BaseStrategy.get_idle():
            base_st.status = StrategyStatus.FETCHING
            base_st.save()
            try:
                markets[(base_st.market, base_st.timeframe)].append(base_st)
            except KeyError:
                markets[(base_st.market, base_st.timeframe)] = [base_st]

        for market, timeframe in markets:
            t = Task(
                market.base.exchange,
                call="fetch_ohlcv",
                context=markets[(market, timeframe)],
                market=market,
                timeframe=timeframe,
            )
            if self.num_workers == 1:
                t.run()
            else:
                self.proc_queue.put(t)

    def refresh_waiting_strategies(self):
        waiting = [base_st for base_st in BaseStrategy.get_waiting()]

        for base_st in waiting:
            t = Task(base_st)
            if self.num_workers == 1:
                t.run()
            else:
                self.proc_queue.put(t)

    def refresh_pending_positions(self):
        for position in Position.get_pending():
            t = Task(position)
            if self.num_workers == 1:
                t.run()
            else:
                self.proc_queue.put(t)

    def refresh_risk(self):
        pass

    # TODO risk assessment:
    # - red flag -- exit all positions
    # - yellow flag -- new buy signals ignored & reduce curr. positions
    # - green flag -- all signals are respected
    # in general, account for overall market risk and volatility
    # maybe use GARCH to model volatility, or a machine learning model
    # maybe user.max_risk and user.max_volatility


class Task:
    target = None
    call = None
    context = None
    kwargs = None
    log_context = None

    def __init__(self, target, call=None, context=None, **kwargs):
        self.target = target
        self.call = call if call is not None else "refresh"
        self.context = context if context is not None else [target]
        self.kwargs = kwargs
        self.log_context = f"{self.target.__class__.__name__}_{self.target.id}".lower()

    def reset(self):
        from sliver.exchange import Exchange
        from sliver.exchanges.factory import ExchangeFactory
        from sliver.position import Position
        from sliver.strategies.factory import StrategyFactory
        from sliver.strategy import BaseStrategy

        if self.target._meta.table_name == "exchange":
            target = Exchange.get(id=self.target.id)
            self.target = ExchangeFactory.from_base(target)
        if self.target._meta.table_name == "strategy":
            target = BaseStrategy.get(id=self.target.id)
            self.target = StrategyFactory.from_base(target)

        for c in self.context:
            if c._meta.table_name == "strategy":
                new = BaseStrategy.get(id=c.id)
                self.context[self.context.index(c)] = new
            if c._meta.table_name == "position":
                new = Position.get(id=c.id)
                self.context[self.context.index(c)] = new

    def run(self):
        try:
            self.reset()

            if self.call != "check_stops":
                logging.info(
                    f"calling {self.target.__class__.__name__}(id={self.target.id})"
                    f".{self.call} with args {self.kwargs}"
                )

            method = getattr(self.target, self.call)
            method(**self.kwargs)

        except PostponingError as e:
            message = f"{e.__class__.__name__} {e}"

            logging.info(message)
            logging.exception(e, exc_info=True)
            send_message(message=message)

            for c in self.context:
                try:
                    c.postpone(interval_in_minutes=1)
                except AttributeError:
                    pass

        except (
            Exception,
            BaseError,
            DisablingError,
        ) as e:
            message = f"{e.__class__.__name__} {e}"

            logging.info(message)
            logging.exception(e, exc_info=True)
            send_message(message=message)

            for c in self.context:
                try:
                    c.disable()
                except AttributeError:
                    pass


class Worker(multiprocessing.Process):
    def __init__(self, proc_queue, log_queue):
        super().__init__()
        self.proc_queue = proc_queue
        self.log_queue = log_queue
        db.init()

    def run(self):
        while True:
            task = self.proc_queue.get()
            logging.config.dictConfig(
                {
                    "version": 1,
                    "disable_existing_loggers": True,
                    "formatters": {
                        "default": {
                            "format": "%(asctime)s -- %(message)s",
                            "datefmt": "%Y-%m-%d %H:%M:%S",
                            "converter": time.gmtime,
                        }
                    },
                    "filters": {
                        "context": {
                            "()": TaskFilter,
                            "context": task.log_context,
                        },
                    },
                    "handlers": {
                        "queue": {
                            "class": "logging.handlers.QueueHandler",
                            "queue": self.log_queue,
                            "filters": ["context"],
                            "formatter": "default",
                        }
                    },
                    "root": {"handlers": ["queue"], "level": "INFO"},
                }
            )
            task.run()


class LogHandler:
    context = None

    def handle(self, record):
        if hasattr(record, "context"):
            logger = logging.getLogger("context")

            if self.context != record.context:
                self.context = record.context
                logger.handlers = []
                filepath = self.context.split("_")[0]
                filename = self.context.split("_")[1]
                logger.addHandler(get_file_handler(filename, filepath))

        if logger.isEnabledFor(record.levelno):
            logger.handle(record)


class TaskFilter(logging.Filter):
    def __init__(self, context, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.context = context

    def filter(self, record):
        record.context = self.context
        return True


class StdoutFilter(logging.Filter):
    def __init__(self, level, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.level = level

    def filter(self, record):
        return record.levelno <= getattr(logging, self.level)
