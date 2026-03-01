#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD:$HOME/AI/openclaw-factory"
export DB_PATH="/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw.db"
while true; do
  .venv/bin/python -u bots/chat_to_dev/ingest_private_chat_v1.py >> logs/tg_private_poll.log 2>&1 || true
  .venv/bin/python -u bots/ingest_telegram_replies_v1.py >> logs/tg_poll.log 2>&1 || true
  sleep 2
done
