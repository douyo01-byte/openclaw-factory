#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
source /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/activate || exit 1
set -a
source /Users/doyopc/AI/openclaw-factory-daemon/env/github.env || exit 1
set +a
export DB_PATH=/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw.db
export OCLAW_DB_PATH="$DB_PATH"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
while true; do
  python -u bots/dev_pr_automerge_v1.py >> logs/dev_pr_automerge_v1.out 2>> logs/dev_pr_automerge_v1.err || true
  sleep 20
done
