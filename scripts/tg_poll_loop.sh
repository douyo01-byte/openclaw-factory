#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
exec 0</dev/null
exec 1>>logs/tg_poll_loop.log
exec 2>&1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
test -f env/telegram.env && { set -a; source env/telegram.env; set +a; }
export DB_PATH="${DB_PATH:-$PWD/data/openclaw.db}"
export OCLAW_DB_PATH="${OCLAW_DB_PATH:-$PWD/data/openclaw.db}"
while true; do
  ./scripts/run_py.sh logs/tg_private_poll.log bots/chat_to_dev/ingest_private_chat_v1.py || true
  ./scripts/run_py.sh logs/tg_poll.log bots/ingest_telegram_replies_v1.py || true
  sleep 2
done
