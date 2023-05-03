import time

from sliver.alert import send_message
from sliver.config import Config
from sliver.exceptions import (
    BaseError,
    DisablingError,
    PostponingError,
)
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
    position = None
    strategy = None
    user_strat = None

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

    def run(call):
        def inner(self, *args, **kwargs):
            try:
                call(self, *args, **kwargs)

            except PostponingError as e:
                self.print(exception=e)
                if self.position:
                    self.position.postpone(interval_in_minutes=5)
                if self.strategy:
                    self.strategy.postpone(interval_in_minutes=5)

            except (
                Exception,
                BaseError,
                DisablingError,
            ) as e:
                self.print(exception=e)
                if self.user_strat:
                    self.user_strat.disable()
                if self.strategy:
                    self.strategy.disable()

        return inner

    @run
    def refresh_risk(self):
        pass
        # TODO risk assessment:
        # - red flag -- exit all positions
        # - yellow flag -- new buy signals ignored & reduce curr. positions
        # - green flag -- all signals are respected
        # in general, account for overall market risk and volatility
        # maybe use GARCH to model volatility, or a machine learning model
        # maybe user.max_risk and user.max_volatility

    @run
    def refresh_opening_positions(self):
        for position in Position.get_opening():
            self.position = position
            self.user_strat = position.user_strategy

            stopped = position.refresh_stops()
            if stopped:
                position.refresh()

            self.user_strat = None
            self.position = None

    @run
    def refresh_pending_strategies(self):
        for base_st in BaseStrategy.get_pending():
            strategy = StrategyFactory.from_base(base_st)

            self.strategy = strategy
            strategy.refresh()
            self.strategy = None

            signal = strategy.get_signal()

            for user_strat in strategy.userstrategy_set:
                self.user_strat = user_strat
                user_strat.refresh(signal)
                self.user_strat = None

    @run
    def refresh_pending_positions(self):
        for position in Position.get_pending():
            self.position = position
            self.user_strat = position.user_strategy
            position.refresh()
            self.user_strat = None
            self.position = None
