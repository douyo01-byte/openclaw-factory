#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
python3 bots/fv_copy_final_worker_v1.py
