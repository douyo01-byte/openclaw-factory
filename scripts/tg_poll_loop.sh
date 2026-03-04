#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
source .venv/bin/activate || exit 1
set -a; source env/telegram_daemon.env; set +a
exec .venv/bin/python -u bots/tg_poll_mux_v2.py >> logs/tg_poll.log 2>&1
