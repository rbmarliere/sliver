#!/bin/bash

IP=""
TELEGRAM_BOT_ID=""
TELEGRAM_CHAT_ID=""
TELEGRAM_API="https://api.telegram.org/bot$TELEGRAM_BOT_ID/sendMessage?chat_id=$TELEGRAM_CHAT_ID&text=$(hostname):%20"

if [ -z "$IP" ]; then
    if [ -z "$1" ]; then
        echo "no process name given"
        exit 1
    fi

    if ! pgrep -x "$1" > /dev/null; then
        curl -s "$TELEGRAM_API$1"%20is%20down
    fi

    exit 0
fi

if ! ping -c 1 "$IP" > /dev/null 2>&1; then
    curl -s "$TELEGRAM_API"server%20is%20down
fi
