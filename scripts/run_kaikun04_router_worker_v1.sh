#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1

set -a
[ -f env/openai.env ] && source env/openai.env || true
[ -f env/telegram_kaikun04.env ] && source env/telegram_kaikun04.env || true
set +a

export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"

echo "[worker] OPENAI_API_KEY=${OPENAI_API_KEY:+set}"
echo "[worker] MODEL=${OPENAI_MODEL:-}"

exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/kaikun04_router_worker_v1.py
