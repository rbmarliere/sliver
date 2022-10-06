import telegram

import hypnox


def notify(message):
    try:
        bot = telegram.Bot(hypnox.config["TELEGRAM_KEY"])
        bot.send_message(text=message,
                         chat_id=hypnox.config["TELEGRAM_CHANNEL"])
    except KeyError:
        pass
