#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
mkdir -p logs
while true
do
  python -u bots/reflection_v1.py >> logs/learning.out 2>> logs/learning.err || true
  python -u bots/reflection_worker_v1.py >> logs/learning.out 2>> logs/learning.err || true
  python -u bots/build_decision_patterns.py >> logs/learning.out 2>> logs/learning.err || true
  sleep 60
done
