#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
. .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="$DB_PATH"
export OCLAW_DB_PATH="$DB_PATH"
exec python -u bots/command_apply_daemon_v1.py
