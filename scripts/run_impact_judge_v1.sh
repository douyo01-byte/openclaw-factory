#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export IMPACT_JUDGE_SLEEP="20"
export IMPACT_JUDGE_LIMIT="20"
exec python -u bots/impact_judge_v1.py >> logs/impact_judge_v1.out 2>> logs/impact_judge_v1.err
