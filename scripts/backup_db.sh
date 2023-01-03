#!/bin/bash

DB_USER=""
DB_NAME=""
DB_HOST=""
BKP_DIR=""

# grab first argument of the script
# if it's not empty, use it as the backup directory
if [ -n "$1" ]; then
    BKP_DIR="$1"
fi

mkdir -p "$BKP_DIR"

pushd "$BKP_DIR" || exit 1

CURRENT=$(date +%Y%m%d%H%M%S).tar

if pg_dump -h "$DB_HOST" -U "$DB_USER" -F t "$DB_NAME" > "$CURRENT"; then
    # delete all but the last 5 backups
    ls -t | tail -n +7 | xargs rm -f

    if [ -L current ]; then
        unlink current
    fi
    ln -s "$CURRENT" current
fi

popd || exit 1
