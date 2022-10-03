from . import utils

config = utils.load_json("/../etc/config.json")

from . import db  # noqa: E402
from . import exchange  # noqa: E402
from . import inventory  # noqa: E402
from . import strategy  # noqa: E402
from . import telegram  # noqa: E402
from . import twitter  # noqa: E402
from . import watchdog  # noqa: E402

__all__ = [
    "db", "exchange", "inventory", "strategy", "telegram", "twitter",
    "watchdog"
]
