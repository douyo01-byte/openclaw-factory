#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export DB_PATH="$DB"
export OCLAW_DB_PATH="$DB"
export FACTORY_DB_PATH="$DB"
export KAIKUN02_PYTHON="/Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python"

v="$(launchctl getenv KAIKUN02_EXECUTE 2>/dev/null || true)"
if [[ -n "$v" ]]; then
  export KAIKUN02_EXECUTE="$v"
else
  export KAIKUN02_EXECUTE="${KAIKUN02_EXECUTE:-0}"
fi

exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python bots/kaikun02_executor_bridge_v2.py
