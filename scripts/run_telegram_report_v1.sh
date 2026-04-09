#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export HOME="/Users/doyopc"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
[ -f .venv/bin/activate ] && source .venv/bin/activate || true
set -a
[ -f env/openai.env ] && source env/openai.env || true
[ -f env/telegram.env ] && source env/telegram.env || true
[ -f env/telegram_kaikun04.env ] && source env/telegram_kaikun04.env || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u /Users/doyopc/AI/openclaw-factory-daemon/bots/telegram_report_v1.py
