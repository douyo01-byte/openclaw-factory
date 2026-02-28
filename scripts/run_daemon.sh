#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory"
source .venv/bin/activate
set -a
. ./.env.openclaw
set +a
: "${DB_PATH:?}"
: "${TELEGRAM_BOT_TOKEN:?}"
: "${TELEGRAM_CHAT_ID:?}"
export OCLAW_DB_PATH="$DB_PATH"
export OCLAW_TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
export OCLAW_TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID"
exec "$@"
