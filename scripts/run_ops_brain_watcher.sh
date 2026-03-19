#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export TELEGRAM_BOT_TOKEN="$(launchctl getenv TELEGRAM_BOT_TOKEN)"
export TELEGRAM_CHAT_ID="$(launchctl getenv TELEGRAM_CHAT_ID)"
export OPS_BRAIN_MODE="watcher"
export OPS_BRAIN_INTERVAL="30"
export OPS_WATCHER_TARGETS="jp.openclaw.ops_brain_agent_v1|http://127.0.0.1:8787/health|60|required,jp.openclaw.dev_pr_automerge_v1||120|observe,jp.openclaw.db_integrity_watchdog_v1||10|required,jp.openclaw.kaikun02_coo_controller_v1||120|observe"
exec /usr/bin/python3 -u bots/ops_brain_v1.py >> logs/ops_brain_watcher.out 2>> logs/ops_brain_watcher.err
