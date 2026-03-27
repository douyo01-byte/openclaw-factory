#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"

set -a
source env/telegram_replies.env
source env/telegram_report.env 2>/dev/null || true
if [ -f "$HOME/AI/openclaw-factory/env/openai.env" ]; then
  set +e
  source "$HOME/AI/openclaw-factory/env/openai.env" 2>/dev/null
  set -e
fi
[ -n "${TELEGRAM_REPORT_BOT_TOKEN:-}" ] && export TELEGRAM_BOT_TOKEN="$TELEGRAM_REPORT_BOT_TOKEN"
[ -n "${CEO_CHAT_ID:-}" ] && export TELEGRAM_CHAT_ID="$CEO_CHAT_ID"
set +a

python3 bots/conversation_outbox_sender_v1.py
