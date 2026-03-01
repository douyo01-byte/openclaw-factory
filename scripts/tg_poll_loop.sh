#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source .venv/bin/activate
export PYTHONPATH=$PWD
export PYTHONUNBUFFERED=1
while true; do
  /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python bots/ingest_telegram_replies_v1.py >> logs/tg_poll.log 2>&1
  sleep 10
done
