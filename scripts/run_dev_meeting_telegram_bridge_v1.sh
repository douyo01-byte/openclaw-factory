#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
set -a
source env/openai.env 2>/dev/null || true
source env/telegram.env 2>/dev/null || true
source env/telegram_daemon.env 2>/dev/null || true
source env/telegram_replies.env 2>/dev/null || true
source env/telegram_report.env 2>/dev/null || true
source env/telegram_routing.env 2>/dev/null || true
set +a
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
exec python -u bots/dev_meeting_telegram_bridge_v1.py
