#!/usr/bin/env bash
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="$HOME/AI/openclaw-factory//Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db"
export OCLAW_DB_PATH="$HOME/AI/openclaw-factory//Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db"
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
while true; do
  ./scripts/update_pr_created.sh >> logs/update_pr_created.out 2>> logs/update_pr_created.err || true
  sleep 60
done
