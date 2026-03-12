#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source /Users/doyopc/AI/openclaw-factory/env/telegram_kaikun03.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory/env/telegram.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory/env/telegram_daemon.env 2>/dev/null || true
source /Users/doyopc/AI/openclaw-factory/env/telegram_report.env 2>/dev/null || true
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
exec python -u -m bots.tg_send_reflection_v1 >> logs/tg_send_reflection_v1.out 2>> logs/tg_send_reflection_v1.err
