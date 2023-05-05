import threading
import time

from sliver.alert import send_message
from sliver.config import Config
from sliver.exceptions import (
    BaseError,
    DisablingError,
    PostponingError,
)
from sliver.exchanges.factory import ExchangeFactory
from sliver.position import Position
from sliver.strategies.factory import StrategyFactory
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
    def __init__(self, log="watchdog"):
        self.logger = log

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

    def run_loop(self):
        while True:
            try:
                self.refresh_risk()
                self.refresh_opening_positions()
                self.refresh_pending_strategies()
                self.refresh_pending_positions()

                time.sleep(int(Config().WATCHDOG_INTERVAL))

            except (BaseError, KeyboardInterrupt):
                break

    def refresh_risk(self):
        pass
        # TODO risk assessment:
        # - red flag -- exit all positions
        # - yellow flag -- new buy signals ignored & reduce curr. positions
        # - green flag -- all signals are respected
        # in general, account for overall market risk and volatility
        # maybe use GARCH to model volatility, or a machine learning model
        # maybe user.max_risk and user.max_volatility

    def refresh_opening_positions(self):
        threads = []
        for position in Position.get_opening():
            t = Refresher(position, call="check_stops")
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    def refresh_pending_strategies(self):
        pending = [base_st for base_st in BaseStrategy.get_pending()]
        markets = [(p.market, p.timeframe) for p in pending]

        threads = []
        for market, timeframe in list(set(markets)):
            exchange = ExchangeFactory.from_base(market.base.exchange)
            t = threading.Thread(target=exchange.fetch_ohlcv, args=(market, timeframe))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        threads = []
        for base_st in BaseStrategy.get_pending():
            strategy = StrategyFactory.from_base(base_st)
            t = Refresher(strategy)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    def refresh_pending_positions(self):
        threads = []
        for position in Position.get_pending():
            t = Refresher(position)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()


class Refresher(threading.Thread):
    target = None
    call = None

    def __init__(self, obj, call="refresh"):
        super().__init__()
        self.target = obj
        self.call = call

    def run(self):
        try:
            method = getattr(self.target, self.call)
            method()

        except PostponingError as e:
            Watchdog().print(exception=e)
            self.target.postpone(interval_in_minutes=5)

        except (
            Exception,
            BaseError,
            DisablingError,
        ) as e:
            Watchdog().print(exception=e)
            self.target.disable()
