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
    config = None

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
            "LOGS_DIR",
            "MODELS_DIR",
            "TELEGRAM_API_HASH",
            "TELEGRAM_API_ID",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHANNEL",
            "TWITTER_BEARER_TOKEN",
            "WATCHDOG_INTERVAL",
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
            raise BaseError("LOGS_DIR={d} not found".format(d=config["LOGS_DIR"]))
        if not os.path.exists(config["MODELS_DIR"]):
            raise BaseError("MODELS_DIR={d} not found".format(d=config["MODELS_DIR"]))
        if config["ENV_NAME"] not in ["development", "production"]:
            raise BaseError(
                "ENV_NAME={d} must be 'development' or 'production'".format(
                    d=config["ENV_NAME"]
                )
            )

        self.config = config

    def __getattr__(self, key):
        return self.config[key]
