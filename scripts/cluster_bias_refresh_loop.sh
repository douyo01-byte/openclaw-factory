#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

mkdir -p logs

while true; do
  python3 bots/cluster_bias_refresh_v1.py >> logs/cluster_bias_refresh.out 2>> logs/cluster_bias_refresh.err || true
  python3 bots/project_decider_v1.py >> logs/cluster_bias_refresh.out 2>> logs/cluster_bias_refresh.err || true
  python3 bots/decider_feedback_learning_v1.py >> logs/cluster_bias_refresh.out 2>> logs/cluster_bias_refresh.err || true
  sleep 600
done
