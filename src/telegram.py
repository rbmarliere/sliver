import src as hypnox
import telegram


def notify(message):
    try:
        bot = telegram.Bot(hypnox.config.config["TELEGRAM_KEY"])
        bot.send_message(text=message,
                         chat_id=hypnox.config.config["TELEGRAM_CHANNEL"])
    except KeyError:
        pass
