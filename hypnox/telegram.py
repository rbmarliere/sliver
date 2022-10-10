import telegram

import hypnox


def notify(message):
    try:
        bot = telegram.Bot(hypnox.config["HYPNOX_TELEGRAM_KEY"])
        bot.send_message(text=message,
                         chat_id=hypnox.config["HYPNOX_TELEGRAM_CHANNEL"])
    except KeyError:
        pass
