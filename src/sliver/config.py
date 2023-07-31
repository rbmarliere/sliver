import os
import sys
import time

import dotenv

from sliver.exceptions import BaseError


class ConfigMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(ConfigMeta, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]


class Config(metaclass=ConfigMeta):
    config = {}

    def __init__(self):
        os.environ["TZ"] = "UTC"
        time.tzset()

        dotenv.load_dotenv()

        config = [
            "DB_HOST",
            "DB_NAME",
            "DB_PASSWORD",
            "DB_USER",
            "ENV_NAME",
            "JWT_SECRET_KEY",
            "ETC_DIR",
            "LOGS_DIR",
            "MODELS_DIR",
            "TELEGRAM_API_HASH",
            "TELEGRAM_API_ID",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHANNEL",
            "WATCHDOG_INTERVAL",
            "HYPNOX_TWITTER_ACCOUNT",
            "HYPNOX_TWITTER_PASSWORD",
            "HYPNOX_TWITTER_PHONE",
            "HYPNOX_TWITTER_SCRAPER_TIMEOUT",
        ]

        error = False
        for var in config:
            if var not in os.environ:
                print(var + " not found in environment!")
                error = True
        if error:
            sys.exit(1)

        config = dict(zip(config, [os.environ[var] for var in config]))

        if not os.path.exists(config["ETC_DIR"]):
            raise BaseError(f"ETC_DIR={config['ETC_DIR']} not found")
        if not os.path.exists(config["LOGS_DIR"]):
            raise BaseError(f"LOGS_DIR={config['LOGS_DIR']} not found")
        if not os.path.exists(config["MODELS_DIR"]):
            raise BaseError(f"MODELS_DIR={config['MODELS_DIR']} not found")
        if config["ENV_NAME"] not in ["development", "production"]:
            raise BaseError(
                f"ENV_NAME={config['ENV_NAME']} must be 'development' or 'production'"
            )

        self.config = config

    def __getattr__(self, key):
        return self.config[key]
