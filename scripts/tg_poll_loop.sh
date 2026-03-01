#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
while true; do
  python -u bots/ingest_telegram_replies_v1.py >> logs/tg_poll.log 2>&1 || true
  sleep 2
done
