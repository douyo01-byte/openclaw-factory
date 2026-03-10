#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
source /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/activate || exit 1
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
exec python -u bots/project_brain_v4.py >> logs/project_brain_v4.out 2>> logs/project_brain_v4.err
