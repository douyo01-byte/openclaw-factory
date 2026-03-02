#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export GITHUB_REPO="douyo01-byte/openclaw-factory"
export TELEGRAM_BOT_TOKEN="$(launchctl getenv TELEGRAM_BOT_TOKEN)"
while true; do
  echo "[supervisor] 20 20 12 61 79 80 81 33 98 100 204 250 395 398 399 400 701date -u +%F\ %T) tick"
  python bots/ingest_telegram_replies_v1.py || true
  python bots/dev_pr_watcher_v1.py || true
  python bots/auto_fix_v1.py || true
  python bots/ci_guard_v1.py || true
  python bots/refiner_guard_v1.py || true
  python bots/decompose_trigger_v1.py || true
  python bots/status_sync_v1.py || true
  sleep 5
done
