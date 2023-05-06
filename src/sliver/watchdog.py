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
from sliver.exchange import Exchange
from sliver.exchanges.factory import ExchangeFactory
from sliver.position import Position
from sliver.strategies.factory import StrategyFactory
from sliver.strategies.status import StrategyStatus
from sliver.strategy import BaseStrategy
from sliver.utils import get_logger


class WatchdogMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(WatchdogMeta, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]


class Watchdog(metaclass=WatchdogMeta):
    def __init__(self, log="watchdog", sync=False):
        self.logger = log
        self.queue = multiprocessing.SimpleQueue()
        self.sync = sync

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        stdout = get_logger(logger)
        stderr = get_logger(logger + "_err", suppress_output=True)

        self._logger = (stdout, stderr)

    def print(self, message=None, exception=None, notice=False):
        stdout = self.logger[0]
        stderr = self.logger[1]

        if exception:
            exception_msg = f"{exception.__class__.__name__} {exception}"
            if message:
                message = f"{message} {exception_msg}"
            else:
                message = exception_msg
            stderr.exception(exception, exc_info=True)

        if exception or notice:
            send_message(message=message)

        stdout.info(message)

    def run(self):
        if not self.sync:
            for cpu in range(multiprocessing.cpu_count()):
                p = Worker(self.queue)
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
                self.queue.put(t)

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
            exchange = ExchangeFactory.from_base(market.base.exchange)
            t = Task(
                exchange,
                call="fetch_ohlcv",
                context=markets[(market, timeframe)],
                market=market,
                timeframe=timeframe,
            )
            if self.sync:
                t.run()
            else:
                self.queue.put(t)

    def refresh_waiting_strategies(self):
        waiting = [base_st for base_st in BaseStrategy.get_waiting()]

        for base_st in waiting:
            t = Task(base_st)
            if self.sync:
                t.run()
            else:
                self.queue.put(t)

    def refresh_pending_positions(self):
        for position in Position.get_pending():
            t = Task(position)
            if self.sync:
                t.run()
            else:
                self.queue.put(t)

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

    def reset(self):
        if self.target._meta.table_name == "exchange":
            print("exchange target")
            target = globals()["Exchange"].get(id=self.target.id)
            self.target = globals()["ExchangeFactory"].from_base(target)
        if self.target._meta.table_name == "strategy":
            print("strategy target")
            target = globals()["BaseStrategy"].get(id=self.target.id)
            self.target = globals()["StrategyFactory"].from_base(target)

        for c in self.context:
            if c._meta.table_name == "strategy":
                new = globals()["BaseStrategy"].get(id=c.id)
                self.context[self.context.index(c)] = new
            if c._meta.table_name == "position":
                new = globals()["Position"].get(id=c.id)
                self.context[self.context.index(c)] = new

    def run(self):
        self.reset()

        try:
            Watchdog().print(
                f"calling {self.target.__class__.__name__}(id={self.target.id})"
                f".{self.call} with args {self.kwargs}"
            )

            method = getattr(self.target, self.call)
            method(**self.kwargs)

        except PostponingError as e:
            Watchdog().print(exception=e)
            for c in self.context:
                try:
                    c.postpone(interval_in_minutes=1)
                except AttributeError:
                    Watchdog().print(
                        f"cannot postpone {c.__class__.__name__}(id={c.id})"
                    )

        except (
            Exception,
            BaseError,
            DisablingError,
        ) as e:
            Watchdog().print(exception=e)
            for c in self.context:
                try:
                    c.disable()
                except AttributeError:
                    Watchdog().print(
                        f"cannot disable {c.__class__.__name__}(id={c.id})"
                    )


class Worker(multiprocessing.Process):
    def __init__(self, queue):
        super().__init__(daemon=True)
        self.queue = queue
        db_init()

    def run(self):
        while True:
            task = self.queue.get()
            task = threading.Thread(
                target=task.run,
                daemon=True,
            )
            task.start()
