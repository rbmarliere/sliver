import time

import telethon.sync
import telegram

from sliver.config import Config
from sliver.print import print
from sliver.exceptions import DisablingError


def get_client(entity_type):
    assert Config().LOGS_DIR
    assert Config().TELEGRAM_API_ID
    assert Config().TELEGRAM_API_HASH

    session = Config().LOGS_DIR + "/telethon_" + entity_type
    api_id = Config().TELEGRAM_API_ID
    api_hash = Config().TELEGRAM_API_HASH

    return telethon.TelegramClient(session, api_id, api_hash)


def telethon_call(entity_type):
    def outer(call):
        def inner(**kwargs):
            try:
                assert entity_type in ["user", "bot"]

                client = get_client(entity_type)

                if "entity" not in kwargs:
                    assert Config().TELEGRAM_CHANNEL
                    channel = Config().TELEGRAM_CHANNEL
                    kwargs["entity"] = int(channel)

                if entity_type == "bot":
                    assert Config().TELEGRAM_BOT_TOKEN
                    bot_token = Config().TELEGRAM_BOT_TOKEN
                    client.start(bot_token=bot_token)

                client.connect()

                method = getattr(client, call(**kwargs))
                res = method(**kwargs)

                client.disconnect()

                return res

            except AttributeError:
                print(f"no telethon method {call.__name__}")

            except telethon.errors.AuthKeyUnregisteredError:
                raise DisablingError("no telethon authentication")

            except telethon.errors.FloodWaitError as e:
                time.sleep(e.seconds)

            except (AssertionError, Exception):
                pass

            finally:
                if "client" in locals():
                    client.disconnect()

        return inner

    return outer


@telethon_call("user")
def get_messages(*, entity, limit=1):
    if limit is None or limit > 0:
        print(f"downloading {'all' if limit is None else limit} messages from {entity}")

    return "get_messages"


@telethon_call("bot")
def send_user_message(*, entity, message):
    return "send_message"


@telethon_call("bot")
def send_message(*, entity, message):
    return "send_message"


def get_updates():
    assert Config().TELEGRAM_BOT_TOKEN

    bot = telegram.Bot(Config().TELEGRAM_BOT_TOKEN)

    return bot.get_updates()
