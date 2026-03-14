#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
. .venv/bin/activate || exit 1

set -a
source env/telegram_kaikun03.env 2>/dev/null || true
source env/telegram.env 2>/dev/null || true
set +a

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CEO_BOT_TOKEN:-}" ]; then
  export TELEGRAM_BOT_TOKEN="$TELEGRAM_CEO_BOT_TOKEN"
fi
if [ -z "${BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  export BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
fi

export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="$DB_PATH"
export OCLAW_DB_PATH="$DB_PATH"

exec python -u bots/healthcheck_v1.py
