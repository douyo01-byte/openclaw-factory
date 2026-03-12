#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
exec python -u bots/schema_migration_engine_v1.py >> logs/schema_migration_engine_v1.out 2>> logs/schema_migration_engine_v1.err
