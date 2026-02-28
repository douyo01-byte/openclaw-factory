#!/usr/bin/env bash
set -euo pipefail
INTERVAL_SEC="${INTERVAL_SEC:-10}"
ERROR_SLEEP_SEC="${ERROR_SLEEP_SEC:-60}"
while true; do
  if curl -fsS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" >/dev/null; then
    python -m bots.ingest_telegram_replies_v1 && sleep "$INTERVAL_SEC" || sleep "$ERROR_SLEEP_SEC"
  else
    sleep "$ERROR_SLEEP_SEC"
  fi
done
