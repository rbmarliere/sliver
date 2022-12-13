import sys
import os
import time

import dotenv

# for ccxt requests
os.environ["TZ"] = "Europe/London"
time.tzset()

dotenv.load_dotenv()

config = [
    "HYPNOX_DB_HOST",
    "HYPNOX_DB_NAME",
    "HYPNOX_DB_PASSWORD",
    "HYPNOX_DB_USER",
    "HYPNOX_ENV_NAME",
    "HYPNOX_LOGS_DIR",
    "HYPNOX_MODELS_DIR",
    "HYPNOX_TELEGRAM_CHANNEL",
    "HYPNOX_TELEGRAM_KEY",
    "HYPNOX_TWITTER_ACCESS_KEY",
    "HYPNOX_TWITTER_ACCESS_SECRET",
    "HYPNOX_TWITTER_CONSUMER_KEY",
    "HYPNOX_TWITTER_CONSUMER_SECRET",
]

error = False
for var in config:
    if var not in os.environ:
        print(var + " not found in environment!")
        error = True
if error:
    sys.exit(1)

config = dict(zip(config, [os.environ[var] for var in config]))

if not os.path.exists(config["HYPNOX_LOGS_DIR"]):
    print("HYPNOX_LOGS_DIR=" + config["HYPNOX_LOGS_DIR"] + " not found!")
    sys.exit(1)
if not os.path.exists(config["HYPNOX_MODELS_DIR"]):
    print("HYPNOX_MODELS_DIR=" + config["HYPNOX_MODELS_DIR"] + " not found!")
    sys.exit(1)
if config["HYPNOX_ENV_NAME"] not in ["development", "production"]:
    print("HYPNOX_ENV_NAME must be 'development' or 'production'!")
    sys.exit(1)

from . import (
    utils,
    db,
    errors,
    exchange,
    inventory,
    models,
    strategy,
    telegram,
    twitter,
    watchdog)

__all__ = [
    "utils",
    "db",
    "errors",
    "exchange",
    "inventory",
    "models",
    "strategy",
    "telegram",
    "twitter",
    "watchdog"
]
