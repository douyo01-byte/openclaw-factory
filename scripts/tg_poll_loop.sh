#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
while true; do
  ./scripts/run_py.sh logs/tg_private_poll.log bots/chat_to_dev/ingest_private_chat_v1.py || true
  ./scripts/run_py.sh logs/tg_poll.log bots/ingest_telegram_replies_v1.py || true
  sleep 2
done
