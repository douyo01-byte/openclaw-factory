#!/bin/bash
cd ~/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export OCLAW_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
if [ -f env/telegram.env ]; then
  set -a
  source env/telegram.env
  set +a
fi
python bots/dev_merge_notify_v1.py
