#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source env/telegram_kaikun04.env 2>/dev/null || true
source env/openai.env 2>/dev/null || true
source env/telegram.env 2>/dev/null || true
set +a
export TELEGRAM_CHAT_ID="512370342"
export TELEGRAM_CEO_CHAT_ID="$TELEGRAM_CHAT_ID"
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory-daemon
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/secretary_llm_v1.py
