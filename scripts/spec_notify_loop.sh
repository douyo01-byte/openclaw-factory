#!/bin/bash
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source "$HOME/AI/openclaw-factory-daemon/.venv/bin/activate" || exit 1
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
set -a
if [ -f "$HOME/AI/openclaw-factory-daemon/env/telegram_daemon.env" ]; then
  source "$HOME/AI/openclaw-factory-daemon/env/telegram_daemon.env"
elif [ -f "$HOME/AI/openclaw-factory-daemon/env/telegram.env" ]; then
  source "$HOME/AI/openclaw-factory-daemon/env/telegram.env"
fi
set +a
while true
do
  "$HOME/AI/openclaw-factory-daemon/.venv/bin/python" -u "$HOME/AI/openclaw-factory-daemon/bots/spec_notify_v1.py" >> "$HOME/AI/openclaw-factory-daemon/logs/spec_notify_v1.out" 2>> "$HOME/AI/openclaw-factory-daemon/logs/spec_notify_v1.err"
  sleep 5
done
