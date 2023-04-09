#!/bin/bash

IP="10.8.0.1"
TELEGRAM_BOT_ID=""
TELEGRAM_CHAT_ID=""
TELEGRAM_API="https://api.telegram.org/bot$TELEGRAM_BOT_ID/sendMessage?chat_id=$TELEGRAM_CHAT_ID&text=$(hostname):%20"
SERVICES=("pdm run serve" "pdm run stream" "pdm run watch")

if ! ping -w 2 -c 1 "$IP" > /dev/null 2>&1; then
   sudo systemctl restart openvpn.service
fi

if ! ping -w 2 -c 1 "$IP" > /dev/null 2>&1; then
   curl -s "$TELEGRAM_API"server%20is%20down
fi

for service in "${SERVICES[@]}"; do
   if [ $(pgrep -f "$service" | wc -l) -eq 0 ] ; then
      curl -s "$TELEGRAM_API"service%20\`"$service"\`%20is%20down
   fi
done
