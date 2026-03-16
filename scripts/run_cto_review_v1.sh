#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export HOME="/Users/doyopc"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
[ -f env/telegram_kaikun04.env ] && source env/telegram_kaikun04.env
[ -f env/openai.env ] && source env/openai.env
set +a
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export DB_PATH="$DB"
export FACTORY_DB_PATH="$DB"
export OCLAW_DB_PATH="$DB"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/cto_review_v1.py
