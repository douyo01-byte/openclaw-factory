#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export DB_PATH="$DB"
export OCLAW_DB_PATH="$DB"
export FACTORY_DB_PATH="$DB"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
set -a
[ -f env/telegram_kaikun02.env ] && source env/telegram_kaikun02.env || true
[ -f env/telegram.env ] && source env/telegram.env || true
set +a
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/kaikun02_router_worker_v1.py
