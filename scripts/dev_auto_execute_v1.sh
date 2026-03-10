#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon"
db="$HOME/AI/openclaw-factory/data/openclaw.db"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export DB_PATH="$db"
export OCLAW_DB_PATH="$db"
set -a
source env/github.env 2>/dev/null || true
source env/telegram_daemon.env 2>/dev/null || source env/telegram.env 2>/dev/null || true
set +a
exec "$HOME/AI/openclaw-factory-daemon/.venv/bin/python" -u bots/dev_auto_execute_v1.py
