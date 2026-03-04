#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="$HOME/AI/openclaw-factory-daemon/data/openclaw.db"
while true; do
  python bots/decompose_trigger_v1.py || true
  sleep 5
done
