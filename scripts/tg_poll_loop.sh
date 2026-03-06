#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$PWD"
export DB_PATH="$HOME/AI/openclaw-factory-daemon/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
mkdir -p logs
while true; do
  set -a; source env/telegram_replies.env; source "$HOME/AI/openclaw-factory/env/openai.env" 2>/dev/null || true; set +a
  python -u bots/ingest_telegram_replies_v1.py >> logs/tg_poll.log 2>&1 || true
  .venv/bin/python -u bots/ingest_spec_answers_v1.py >> logs/tg_poll.log 2>&1 || true
  .venv/bin/python -u bots/meeting_orchestrator_v1.py >> logs/tg_poll.log 2>&1 || true
.venv/bin/python -u $HOME/AI/openclaw-factory/bots/spec_refiner_v2.py >> logs/refiner.log 2>&1 || true

  sleep 2
done
