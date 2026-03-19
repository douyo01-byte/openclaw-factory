#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export OPS_BRAIN_MODE="watcher"
export OPS_BRAIN_INTERVAL="30"
export OPS_WATCHER_TARGETS="http://127.0.0.1:8787/health"
exec /usr/bin/python3 -u bots/ops_brain_v1.py >> logs/ops_brain_watcher.out 2>> logs/ops_brain_watcher.err
