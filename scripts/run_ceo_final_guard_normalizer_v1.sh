#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon
source .venv/bin/activate
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export PYTHONPATH="$PWD"
python bots/ceo_final_guard_normalizer_v1.py
