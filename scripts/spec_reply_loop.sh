#!/bin/bash
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export DB_PATH="$HOME/AI/openclaw-factory-daemon/data/openclaw_real.db"
set -a
if [ -f env/telegram_daemon.env ]; then
  source env/telegram_daemon.env
elif [ -f env/telegram.env ]; then
  source env/telegram.env
fi
set +a
while true
do
  python -u bots/ingest_spec_reply_v1.py >> logs/spec_reply_v1.out 2>> logs/spec_reply_v1.err
  sleep 5
done
