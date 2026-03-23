#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source env/telegram.env 2>/dev/null || true
source env/openai.env 2>/dev/null || true
source env/telegram_kaikun04.env 2>/dev/null || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/ingest_private_replies_kaikun04.py
