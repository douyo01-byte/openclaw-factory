#!/usr/bin/env bash
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db"
exec python -u bots/company_dashboard_v1.py
