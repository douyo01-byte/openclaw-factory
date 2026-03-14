#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
set -a
[ -f env/openai.env ] && source env/openai.env
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/executor_guard_v2.py
