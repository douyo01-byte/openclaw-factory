#!/usr/bin/env bash
set -euo pipefail
INTERVAL_SEC="${INTERVAL_SEC:-10}"
while true; do
  python -m bots.ingest_telegram_replies_v1 || true
  sleep "$INTERVAL_SEC"
done
