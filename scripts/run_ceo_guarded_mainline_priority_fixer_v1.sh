#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec python -u bots/ceo_guarded_mainline_priority_fixer_v1.py
