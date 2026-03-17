#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
exec python -u bots/ceo_problem_detector_v1.py
