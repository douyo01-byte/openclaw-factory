#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
. .venv/bin/activate || exit 1
set -a
source env/telegram.env 2>/dev/null || true
source env/telegram_routing.env 2>/dev/null || true
source env/telegram_report.env 2>/dev/null || true
source env/telegram_private.env 2>/dev/null || true
source env/openai.env 2>/dev/null || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
echo "[secretary_runner] OPENAI_API_KEY_LEN=${#OPENAI_API_KEY}"
echo "[secretary_runner] TELEGRAM_BOT_TOKEN_LEN=${#TELEGRAM_BOT_TOKEN}"
echo "[secretary_runner] TELEGRAM_CEO_BOT_TOKEN_LEN=${#TELEGRAM_CEO_BOT_TOKEN}"
echo "[secretary_runner] TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}"
exec python -u bots/secretary_llm_v1.py
