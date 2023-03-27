def print(message=None, exception=None):
    from .watchdog import Watchdog

    return Watchdog().print(message, exception)
