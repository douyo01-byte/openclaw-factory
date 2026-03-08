#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
source .venv/bin/activate || exit 1
export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
while true; do
  echo "[$(date '+%F %T')] bots/project_brain_v4.py" >> logs/brain_supply.out
  python -u bots/project_brain_v4.py >> logs/brain_supply.out 2>> logs/brain_supply.err || true
  sleep 600
done
