import logging
import logging.config
import multiprocessing
import threading
import time

from sliver.alert import send_message
from sliver.config import Config
from sliver.database import db_init
from sliver.exceptions import (
    BaseError,
    DisablingError,
    PostponingError,
)
from sliver.position import Position
from sliver.strategies.status import StrategyStatus
from sliver.strategy import BaseStrategy


# def get_file_handler(filename):
#     formatter = logging.Formatter("%(asctime)s -- %(message)s")
#     formatter.converter = time.gmtime

#     log_file = f"{Config().LOGS_DIR}/{filename}.log"
#     file_handler = logging.handlers.RotatingFileHandler(
#         log_file, maxBytes=52428800, backupCount=32  # 50mb
#     )
#     file_handler.setFormatter(formatter)

#     return file_handler


class Watchdog:
    def __init__(self, sync=False):
        self.sync = sync
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
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": "INFO",
                        "formatter": "default",
                    }
                },
                # "loggers": {
                #     "foo": {"handlers": ["console"], "level": "INFO"},
                # },
                "root": {"handlers": ["console"], "level": "INFO"},
            }
        )

        if not self.sync:
            logging.handlers.QueueListener(self.log_queue).start()
            for cpu in range(multiprocessing.cpu_count()):
                p = Worker(self.proc_queue, self.log_queue)
                p.start()

        db_init()
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
            if self.sync:
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
            if self.sync:
                t.run()
            else:
                self.proc_queue.put(t)

    def refresh_waiting_strategies(self):
        waiting = [base_st for base_st in BaseStrategy.get_waiting()]

        for base_st in waiting:
            t = Task(base_st)
            if self.sync:
                t.run()
            else:
                self.proc_queue.put(t)

    def refresh_pending_positions(self):
        for position in Position.get_pending():
            t = Task(position)
            if self.sync:
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

    def __init__(self, target, call=None, context=None, **kwargs):
        self.target = target
        self.call = call if call is not None else "refresh"
        self.context = context if context is not None else [target]
        self.kwargs = kwargs

        # h = get_file_handler(f"{self.target.__class__.__name__}_{self.target.id}")
        # h.addFilter(lambda record: record.levelno >= logging.INFO)
        # logger = logging.getLogger()
        # logger.addHandler(h)

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

        finally:
            ...
            # logging.removeHandler(self.handler)


class Worker(multiprocessing.Process):
    def __init__(self, proc_queue, log_queue):
        super().__init__(daemon=True)
        self.proc_queue = proc_queue

        qh = logging.handlers.QueueHandler(log_queue)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(qh)

        # logging.config.dictConfig(
        #     {
        #         "version": 1,
        #         "disable_existing_loggers": True,
        #         "handlers": {
        #             "queue": {
        #                 "class": "logging.handlers.QueueHandler",
        #                 "queue": log_queue,
        #             }
        #         },
        #         "root": {"handlers": ["queue"], "level": "INFO"},
        #     }
        # )

        logging.info("hai")

        db_init()

    def run(self):
        while True:
            task = self.proc_queue.get()
            task = threading.Thread(
                target=task.run,
                daemon=True,
            )
            task.start()


class LogHandler:
    def handle(self, record):
        if record.name == "root":
            logger = logging.getLogger("console")
        else:
            logger = logging.getLogger(record.name)

        if logger.isEnabledFor(record.levelno):
            print(logger)
            print(record)
            logger.handle(record)

        # if logger.isEnabledFor(record.levelno):
        #     # The process name is transformed just to show that it's the listener
        #     # doing the logging to files and console
        #     record.processName = "foo"
        #     logger.handle(record)
