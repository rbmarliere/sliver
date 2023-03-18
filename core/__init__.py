import os
import sys
import time

import dotenv


# for ccxt requests
os.environ["TZ"] = "Europe/London"
time.tzset()

dotenv.load_dotenv()

config = [
    "DB_HOST",
    "DB_NAME",
    "DB_PASSWORD",
    "DB_USER",
    "ENV_NAME",
    "LOGS_DIR",
    "MODELS_DIR",
    "TELEGRAM_API_HASH",
    "TELEGRAM_API_ID",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHANNEL",
    "TWITTER_BEARER_TOKEN",
    "WATCHDOG_INTERVAL"
]

error = False
for var in config:
    if var not in os.environ:
        print(var + " not found in environment!")
        error = True
if error:
    sys.exit(1)

config = dict(zip(config, [os.environ[var] for var in config]))

if not os.path.exists(config["LOGS_DIR"]):
    print("LOGS_DIR=" + config["LOGS_DIR"] + " not found!")
    sys.exit(1)
if not os.path.exists(config["MODELS_DIR"]):
    print("MODELS_DIR=" + config["MODELS_DIR"] + " not found!")
    sys.exit(1)
if config["ENV_NAME"] not in ["development", "production"]:
    print("ENV_NAME must be 'development' or 'production'!")
    sys.exit(1)


from . import (  # noqa 402
    alert,
    db,
    errors,
    inventory,
    utils,
    watchdog)
__all__ = [
    "alert",
    "db",
    "errors",
    "inventory",
    "utils",
    "watchdog"
]

import strategies  # noqa 402
import exchanges  # noqa 402
