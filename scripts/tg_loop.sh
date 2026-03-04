#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="$HOME/AI/openclaw-factory-daemon/data/openclaw.db"
export TELEGRAM_BOT_TOKEN="$(launchctl getenv TELEGRAM_BOT_TOKEN)"
while true; do
  python bots/ingest_telegram_replies_v1.py || true
  sleep 5
done
