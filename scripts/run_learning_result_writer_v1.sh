#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
. .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="$DB_PATH"
export OCLAW_DB_PATH="$DB_PATH"
exec python -u bots/learning_result_writer_v1.py
