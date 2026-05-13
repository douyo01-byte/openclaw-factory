#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon
set -a
[ -f env/openai.env ] && source env/openai.env || true
[ -f env/telegram.env ] && source env/telegram.env || true
[ -f env/telegram_kaikun04.env ] && source env/telegram_kaikun04.env || true
set +a
export DB_PATH="${DB_PATH:-/Users/doyopc/AI/openclaw-factory/data/openclaw.db}"
export FACTORY_DB_PATH="$DB_PATH"
export OCLAW_DB_PATH="$DB_PATH"
export TELEGRAM_DIGEST_DRY_RUN="${TELEGRAM_DIGEST_DRY_RUN:-0}"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -m bots.telegram_digest_v1
