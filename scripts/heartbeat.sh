#!/bin/bash

IP=""

TELEGRAM_BOT_ID=""
TELEGRAM_CHAT_ID=""

TELEGRAM_API="https://api.telegram.org/bot$TELEGRAM_BOT_ID/sendMessage?chat_id=$TELEGRAM_CHAT_ID&text=sliver%20is%20down"

if ! ping -c 1 "$IP" > /dev/null 2>&1; then
    curl -s "$TELEGRAM_API"
fi
