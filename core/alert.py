import time

import telegram
import telethon.sync

import core


def send_user_message(user, msg):
    while True:
        try:
            assert core.config["TELEGRAM_BOT_TOKEN"]
            assert user.telegram_username

            bot = telegram.Bot(core.config["TELEGRAM_BOT_TOKEN"])

            if user.telegram_chat_id is None:
                updates = bot.get_updates()
                for update in updates:
                    if update.message.chat.username == user.telegram_username:
                        user.telegram_chat_id = update.message.chat.id
                        user.save()

            bot.send_message(text=msg,
                             chat_id=user.telegram_chat_id)

        except (KeyError, AssertionError):
            pass

        except telegram.error.NetworkError:
            time.sleep(30)
            continue

        break


def send_message(message):
    while True:
        try:
            assert core.config["TELEGRAM_BOT_TOKEN"]
            assert core.config["TELEGRAM_CHANNEL"]

            bot = telegram.Bot(core.config["TELEGRAM_BOT_TOKEN"])

            bot.send_message(text=message,
                             chat_id=core.config["TELEGRAM_CHANNEL"])

        except (KeyError, AssertionError):
            pass

        except telegram.error.NetworkError:
            time.sleep(30)
            continue

        break


def get_messages(username, limit=1):
    while True:
        try:
            assert core.config["LOGS_DIR"]
            assert core.config["TELEGRAM_API_ID"]
            assert core.config["TELEGRAM_API_HASH"]

            session = core.config["LOGS_DIR"] + "/telethon"
            api_id = core.config["TELEGRAM_API_ID"]
            api_hash = core.config["TELEGRAM_API_HASH"]

            global telethon_client
            try:
                telethon_client
            except NameError:
                telethon_client = telethon.TelegramClient(session,
                                                          api_id,
                                                          api_hash)

                telethon_client.connect()

                me = telethon_client.get_me()
                if me is None:
                    raise core.errors.BaseError("no telegram authentication")

            if not telethon_client.is_connected():
                telethon_client.connect()

            if limit is None or limit > 0:
                core.watchdog.info(
                    "downloading {l} messages from {u}"
                    .format(u=username,
                            l="all" if limit is None else limit))

            try:
                m = telethon_client.get_messages(username, limit=limit)
            except telethon.errors.FloodWaitError as e:
                time.sleep(e.seconds)

            telethon_client.disconnect()

            return m

        except Exception as e:
            raise core.errors.BaseError("swapperbox: {err} {e}"
                                        .format(err=e.__class__.__name__,
                                                e=e))
