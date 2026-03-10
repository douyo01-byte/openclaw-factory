#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
source /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/activate || exit 1
set -a
source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_daemon.env || exit 1
set +a
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
exec python -u bots/chat_to_dev/ingest_private_chat_v1.py >> logs/tg_private_poll.log 2>> logs/tg_private_ingest_v1.err
