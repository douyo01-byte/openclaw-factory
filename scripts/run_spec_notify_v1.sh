#!/usr/bin/env bash
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
set -a
for f in "$HOME/AI/openclaw-factory/env/"*.env "$HOME/AI/openclaw-factory-daemon/env/"*.env; do
  [ -f "$f" ] && source "$f"
done
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
set +a
exec python -u bots/spec_notify_v1.py
