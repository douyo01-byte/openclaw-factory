#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/activate || exit 1
set -a
source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_kaikun04.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory-daemon/env/openai.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram.env 2>/dev/null || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u /Users/doyopc/AI/openclaw-factory-daemon/bots/private_reply_to_inbox_v1.py
