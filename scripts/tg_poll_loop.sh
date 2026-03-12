#!/bin/bash
set +u
set -o pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
exec </dev/null >> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll.log 2>> /Users/doyopc/AI/openclaw-factory-daemon/logs/tg_poll.err

export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
export FACTORY_DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
export OCLAW_DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
export TELEGRAM_BOT_TOKEN="${TELEGRAM_CEO_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"

while true; do
  set +e
  set -a
  [ -f /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_replies.env ] && source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_replies.env
  [ -f /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_report.env ] && source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_report.env
  [ -f /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_routing.env ] && source /Users/doyopc/AI/openclaw-factory-daemon/env/telegram_routing.env
  [ -f /Users/doyopc/AI/openclaw-factory/env/openai.env ] && source /Users/doyopc/AI/openclaw-factory/env/openai.env
  export TELEGRAM_BOT_TOKEN="${TELEGRAM_CEO_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
  export TELEGRAM_CHAT_ID="${TELEGRAM_CEO_CHAT_ID:-${CEO_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}}"
  echo "[tg_poll_env] BOT=${TELEGRAM_BOT_TOKEN:0:12} CHAT=${TELEGRAM_CHAT_ID}"
  set +a

  echo "[$(date '+%F %T')] loop_start"
  TELEGRAM_BOT_TOKEN="${TELEGRAM_CEO_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}" TELEGRAM_CHAT_ID="${TELEGRAM_CEO_CHAT_ID:-${CEO_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}}" /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/ingest_telegram_replies_v1.py
  echo "[$(date '+%F %T')] ingest_exit=$?"
  echo "[$(date '+%F %T')] private_chat_start"
  /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/chat_to_dev/ingest_private_chat_v1.py
  echo "[$(date '+%F %T')] private_chat_exit=$?"
  echo "[$(date '+%F %T')] spec_answers_start"
  /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/ingest_spec_answers_v1.py
  echo "[$(date '+%F %T')] spec_answers_exit=$?"

  sleep 2
done
