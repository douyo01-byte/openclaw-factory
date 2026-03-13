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
  python -u bots/chat_to_dev/chat_to_proposal_v1.py >> logs/chat_to_proposal_v1.out 2>> logs/chat_to_proposal_v1.err || true
  sleep 30
done
