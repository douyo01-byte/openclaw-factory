#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export DB_PATH="$DB"
export OCLAW_DB_PATH="$DB"
export FACTORY_DB_PATH="$DB"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"

if [ -f env/telegram_kaikun02.env ]; then
  set -a
  source env/telegram_kaikun02.env
  set +a
else
  echo "missing env/telegram_kaikun02.env" >&2
  exit 1
fi

exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/ingest_private_replies_v1.py >> logs/ingest_private_replies_kaikun02.out 2>> logs/ingest_private_replies_kaikun02.err
