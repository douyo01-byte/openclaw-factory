#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export OPS_BRAIN_MODE="agent"
export OPS_BRAIN_HOST="127.0.0.1"
export OPS_BRAIN_PORT="8787"
exec /usr/bin/python3 -u bots/ops_brain_v1.py >> logs/ops_brain_agent.out 2>> logs/ops_brain_agent.err
