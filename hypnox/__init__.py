from os import environ as env

config = [
    "HYPNOX_DB_HOST",
    "HYPNOX_DB_NAME",
    "HYPNOX_DB_USER",
    "HYPNOX_DB_PASSWORD",
    "HYPNOX_TWITTER_ACCESS_KEY",
    "HYPNOX_TWITTER_ACCESS_SECRET",
    "HYPNOX_TWITTER_CONSUMER_KEY",
    "HYPNOX_TWITTER_CONSUMER_SECRET",
    "HYPNOX_TELEGRAM_KEY",
    "HYPNOX_TELEGRAM_CHANNEL"
]

for var in config:
    assert var in env, var + " not found in environment!"

config = dict(zip(config, [env[var] for var in config]))

from . import (
    utils,
    db,
    exchange,
    inventory,
    strategy,
    telegram,
    twitter,
    watchdog)

__all__ = [
    "utils",
    "db",
    "exchange",
    "inventory",
    "strategy",
    "telegram",
    "twitter",
    "watchdog"
]
