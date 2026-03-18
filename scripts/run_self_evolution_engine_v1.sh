#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
[ -f env/openai.env ] && source env/openai.env
[ -f env/telegram.env ] && source env/telegram.env
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u /Users/doyopc/AI/openclaw-factory-daemon/bots/self_evolution_engine_v1.py >> /Users/doyopc/AI/openclaw-factory-daemon/logs/self_evolution_engine_v1.out 2>> /Users/doyopc/AI/openclaw-factory-daemon/logs/self_evolution_engine_v1.err
