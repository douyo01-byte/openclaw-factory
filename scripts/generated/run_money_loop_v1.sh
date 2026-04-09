#!/bin/bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
[ -f "$HOME/AI/openclaw-factory-daemon/.env" ] && set -a && . "$HOME/AI/openclaw-factory-daemon/.env" && set +a
exec "$HOME/AI/openclaw-factory-daemon/.venv/bin/python" bots/money_loop_v1.py
