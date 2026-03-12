#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
set -a
[ -f env/telegram.env ] && source env/telegram.env
[ -f env/telegram_daemon.env ] && source env/telegram_daemon.env
[ -f env/telegram_routing.env ] && source env/telegram_routing.env
[ -f env/openai.env ] && source env/openai.env
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/auto_execute_now_v1.py >> logs/auto_execute_now_v1.out 2>> logs/auto_execute_now_v1.err
