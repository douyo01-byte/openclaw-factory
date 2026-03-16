#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source env/openai.env 2>/dev/null || true
source env/telegram.env 2>/dev/null || true
source env/telegram_daemon.env 2>/dev/null || true
source env/telegram_replies.env 2>/dev/null || true
source env/telegram_report.env 2>/dev/null || true
source env/telegram_routing.env 2>/dev/null || true
set +a
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export DB_PATH="$DB"
export OCLAW_DB_PATH="$DB"
export FACTORY_DB_PATH="$DB"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export DEV_MERGE_NOTIFY_SLEEP="10"
export DEV_MERGE_NOTIFY_OPENAI_TIMEOUT="45"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/dev_merge_notify_v1.py
