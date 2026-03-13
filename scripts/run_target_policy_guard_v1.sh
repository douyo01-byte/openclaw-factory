#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
source .venv/bin/activate || exit 1
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
while true; do
  python -u bots/target_policy_guard_v1.py >> logs/target_policy_guard_v1.out 2>> logs/target_policy_guard_v1.err || true
  sleep 20
done
