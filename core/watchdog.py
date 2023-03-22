import core


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
        stdout = core.utils.get_logger(logger)
        stderr = core.utils.get_logger(logger + "_err", suppress_output=True)

        self._logger = (stdout, stderr)

    def print(self, message=None, exception=None):
        stdout = self.logger[0]
        stderr = self.logger[1]

        if exception:
            exception_msg = "{e} {err}".format(
                e=exception.__class__.__name__, err=exception
            )
            if message:
                message = "{m} {e}".format(m=message, e=exception_msg)
            else:
                message = exception_msg

            stderr.exception(exception, exc_info=True)
            core.alert.send_message(message)

        stdout.info(message)

    def run_loop(self):
        # self.refresh_risk()
        self.refresh_opening_positions()
        self.refresh_pending_strategies()
        self.refresh_pending_positions()

    def run(call):
        def inner(self, *args, **kwargs):
            try:
                call(self, *args, **kwargs)

            except core.errors.PostponingError as e:
                self.print(exception=e)
                if self.position:
                    self.position.postpone(interval_in_minutes=5)
                if self.strategy:
                    self.strategy.postpone(interval_in_minutes=5)

            except (
                Exception,
                core.errors.BaseError,
                core.errors.ModelTooLarge,
                core.errors.ModelDoesNotExist,
                core.errors.DisablingError,
            ) as e:
                self.print(exception=e)
                if self.user_strat:
                    self.user_strat.disable()
                if self.strategy:
                    self.strategy.disable()

        return inner

    @run
    def refresh_opening_positions(self):
        for position in core.db.get_opening_positions():
            self.position = position
            self.user_strat = position.user_strategy

            stopped = position.check_stops()
            if stopped:
                position.refresh()

            self.user_strat = None
            self.position = None

    @run
    def refresh_pending_positions(self):
        for position in core.db.get_pending_positions():
            self.position = position
            self.user_strat = position.user_strategy

            position.refresh()

            self.user_strat = None
            self.position = None

    @run
    def refresh_pending_strategies(self):
        for strategy in core.db.get_pending_strategies():
            self.strategy = strategy

            strategy.refresh()

            self.strategy = None

            self.refresh_pending_users(strategy.get_active_users())

    @run
    def refresh_pending_users(self, users):
        for user_strat in users:
            self.user_strat = user_strat

            user_strat.refresh()

            self.user_strat = None

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
