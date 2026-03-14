#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
. .venv/bin/activate || exit 1
set -a
[ -f env/telegram_routing.env ] && source env/telegram_routing.env
[ -f env/telegram.env ] && source env/telegram.env
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="$DB_PATH"
export OCLAW_DB_PATH="$DB_PATH"
exec python -u bots/ceo_hub_sender_v1.py
