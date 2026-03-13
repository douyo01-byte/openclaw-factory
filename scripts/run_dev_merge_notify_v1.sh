#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source env/telegram.env 2>/dev/null || true
source env/telegram_daemon.env 2>/dev/null || true
source env/telegram_replies.env 2>/dev/null || true
source env/telegram_report.env 2>/dev/null || true
source env/telegram_routing.env 2>/dev/null || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export DEV_MERGE_NOTIFY_SLEEP="10"
exec python -u bots/dev_merge_notify_v1.py >> logs/dev_merge_notify_v1.out 2>> logs/dev_merge_notify_v1.err
