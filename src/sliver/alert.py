import time

import telethon.sync

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
                    kwargs["entity"] = channel

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


# def send_user_message(self, message):
#     while True:
#         try:
#             assert Config().TELEGRAM_BOT_TOKEN
#             assert self.telegram_username

#             bot = telegram.Bot(Config().TELEGRAM_BOT_TOKEN)

#             if self.telegram_chat_id is None:
#                 updates = bot.get_updates()
#                 for update in updates:
#                     if update.message.chat.username == self.telegram_username:
#                         self.telegram_chat_id = update.message.chat.id
#                         self.save()

#             bot.send_message(text=message, chat_id=self.telegram_chat_id)

#         except (KeyError, AssertionError):
#             pass

#         except telegram.error.NetworkError:
#             time.sleep(30)
#             continue

#         break

# def send_message(self, message):
#     while True:
#         try:
#             assert Config().TELEGRAM_BOT_TOKEN
#             assert Config().TELEGRAM_CHANNEL

#             bot = telegram.Bot(Config().TELEGRAM_BOT_TOKEN)

#             bot.send_message(text=message, chat_id=Config().TELEGRAM_CHANNEL)

#         except (KeyError, AssertionError):
#             pass

#         except telegram.error.NetworkError:
#             time.sleep(30)
#             continue

#         break

if __name__ == "__main__":
    send_message(message="hello world")
