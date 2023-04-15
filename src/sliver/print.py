def print(message=None, exception=None, notice=False):
    from .watchdog import Watchdog

    return Watchdog().print(message, exception, notice)
