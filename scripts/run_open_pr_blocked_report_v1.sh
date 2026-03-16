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
if [ -f env/github.env ]; then
  set -a
  source env/github.env
  set +a
fi
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/open_pr_blocked_report_v1.py
