import telegram

import core


def notice(message):
    try:
        assert core.config["HYPNOX_TELEGRAM_KEY"]
        assert core.config["HYPNOX_TELEGRAM_CHANNEL"]
        bot = telegram.Bot(core.config["HYPNOX_TELEGRAM_KEY"])
        bot.send_message(text=message,
                         chat_id=core.config["HYPNOX_TELEGRAM_CHANNEL"])
    except (KeyError, AssertionError):
        pass
