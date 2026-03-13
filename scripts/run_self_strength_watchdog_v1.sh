#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
python3 -u bots/self_strength_watchdog_v1.py
