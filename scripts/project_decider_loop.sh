#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate
export DB_PATH="$PWD/data/openclaw.db"
while true; do
  python -u bots/project_decider_v1.py || true
  sleep 15
done
