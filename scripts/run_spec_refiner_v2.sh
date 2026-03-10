#!/usr/bin/env bash
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
set -a
source env/openai.env || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
set +a
exec python -u bots/spec_refiner_v2.py
