#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source env/telegram.env 2>/dev/null || true
source env/openai.env 2>/dev/null || true
source env/telegram_kaikun02.env 2>/dev/null || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
export KAIKUN02_ROUTER_BOT_TOKEN="${KAIKUN02_ROUTER_BOT_TOKEN:-$TELEGRAM_BOT_TOKEN}"
export KAIKUN02_ROUTER_CHAT_ID="${KAIKUN02_ROUTER_CHAT_ID:-$TELEGRAM_CHAT_ID}"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/kaikun02_router_worker_v1.py
