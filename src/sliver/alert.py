import time

import telethon.sync
import telegram

from sliver.config import Config
from sliver.print import print
from sliver.exceptions import DisablingError


def telethon_call(entity_type):
    def outer(call):
        def inner(**kwargs):
            try:
                assert Config().LOGS_DIR
                assert Config().TELEGRAM_API_ID
                assert Config().TELEGRAM_API_HASH
                assert Config().TELEGRAM_BOT_TOKEN
                assert Config().TELEGRAM_CHANNEL

                session = Config().LOGS_DIR + "/telethon_" + entity_type
                api_id = Config().TELEGRAM_API_ID
                api_hash = Config().TELEGRAM_API_HASH
                bot_token = Config().TELEGRAM_BOT_TOKEN
                channel = Config().TELEGRAM_CHANNEL

                client = telethon.TelegramClient(session, api_id, api_hash)

                if entity_type == "bot":
                    client.start(bot_token=bot_token)

                if "entity" not in kwargs:
                    kwargs["entity"] = int(channel)

                client.connect()

                method = getattr(client, call.__name__)
                res = method(**kwargs)

                client.disconnect()

                return res

            except AssertionError:
                print("no telegram configuration")

            except AttributeError:
                print("no telethon method {m}".format(m=call.__name__))

            except telethon.errors.FloodWaitError as e:
                time.sleep(e.seconds)

            except Exception as e:
                raise DisablingError("{err} {e}".format(err=e.__class__.__name__, e=e))

        return inner

    return outer


@telethon_call("user")
def get_messages(*, entity, limit=1):
    if limit is None or limit > 0:
        print(
            "downloading {l} messages from {u}".format(
                u=entity, l="all" if limit is None else limit
            )
        )

    return "get_messages"


@telethon_call("bot")
def send_user_message(*, entity, message):
    return "send_message"


@telethon_call("bot")
def send_message(*, message):
    return "send_message"


def get_updates():
    assert Config().TELEGRAM_BOT_TOKEN

    bot = telegram.Bot(Config().TELEGRAM_BOT_TOKEN)

    return bot.get_updates()
