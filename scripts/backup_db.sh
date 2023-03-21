#!/bin/bash

DB_USER=""
DB_NAME=""
DB_HOST="192.168.1.169"
BKP_DIR="$HOME/sliver.db"
TELEGRAM_BOT_ID=""
TELEGRAM_CHAT_ID=""
TELEGRAM_API="https://api.telegram.org/bot$TELEGRAM_BOT_ID/sendMessage?chat_id=$TELEGRAM_CHAT_ID&text=$(hostname):%20"

# grab first argument of the script
# if it's not empty, use it as the backup directory
if [ -n "$1" ]; then
    BKP_DIR="$1"
fi

mkdir -p "$BKP_DIR"

pushd "$BKP_DIR" || exit 1

CURRENT=$(date +%Y%m%d%H%M%S).tar

if pg_dump -h "$DB_HOST" -U "$DB_USER" -F t "$DB_NAME" > "$CURRENT" 2>&1; then
    # delete all but the last 35 backups
    ls -t | tail -n +35 | xargs rm -f

    if [ -L current ]; then
        unlink current
    fi
    ln -s "$CURRENT" current
else
    curl -s "$TELEGRAM_API"database%20backup%20failed
fi

popd || exit 1
