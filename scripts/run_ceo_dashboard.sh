#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
exec python -u bots/company_dashboard_v1.py
