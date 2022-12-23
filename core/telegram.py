import telegram

import core


def notice(message):
    try:
        assert core.config["TELEGRAM_KEY"]
        assert core.config["TELEGRAM_CHANNEL"]
        bot = telegram.Bot(core.config["TELEGRAM_KEY"])
        bot.send_message(text=message,
                         chat_id=core.config["TELEGRAM_CHANNEL"])
    except (KeyError, AssertionError):
        pass
