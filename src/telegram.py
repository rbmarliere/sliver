import src as hypnox
import telegram


def notify(message):
    bot = telegram.Bot(hypnox.config.config["TELEGRAM_KEY"])
    bot.send_message(text=message,
                     chat_id=hypnox.config.config["TELEGRAM_CHANNEL"])
