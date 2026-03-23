#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

python3 bots/cluster_bias_refresh_v1.py
python3 bots/project_decider_v1.py
./scripts/check_cluster_bias_state.sh
./scripts/check_private_reply_flow.sh
