#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
test -f env/telegram.env && { set -a; source env/telegram.env; set +a; }
export DB_PATH="${DB_PATH:-$PWD/data/openclaw.db}"
export OCLAW_DB_PATH="${OCLAW_DB_PATH:-$PWD/data/openclaw.db}"
exec </dev/null
while true; do
  python -u bots/chat_to_dev/ingest_private_chat_v1.py >> logs/tg_private_poll.log 2>&1 || true
  python -u bots/ingest_telegram_replies_v1.py >> logs/tg_poll.log 2>&1 || true
  sleep 2
done
