#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/kaikun04_router_cleanup_v1.py
