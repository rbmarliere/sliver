#!/usr/bin/env python3

import argparse
import asyncio
import os

from telethon import TelegramClient

import core


session = core.cfg("LOGS_DIR") + "/telethon"
api_id = core.cfg("TELEGRAM_API_ID")
api_hash = core.cfg("TELEGRAM_API_HASH")
# bot_token = core.get_config("TELEGRAM_BOT_TOKEN")


async def connect(session):
    if os.path.exists(session + ".session"):
        print("Session file exists")
        return

    client = TelegramClient(session, api_id, api_hash)
    # client.start(bot_token=bot_token)
    await client.start()
    # await client.log_out()


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-s", "--session", help="Session name")
    args = argp.parse_args()

    if args.session:
        session = args.session

    asyncio.run(connect(session))
