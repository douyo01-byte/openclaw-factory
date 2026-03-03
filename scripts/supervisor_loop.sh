#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export GITHUB_REPO="douyo01-byte/openclaw-factory"
export TELEGRAM_BOT_TOKEN="$(launchctl getenv TELEGRAM_BOT_TOKEN)"
while true; do
  echo "[supervisor] $(date -u +%F\ %T) tick"
  python bots/dev_pr_watcher_v1.py || true
  python bots/auto_fix_v1.py || true
  python bots/ci_guard_v1.py || true
  python bots/refiner_guard_v1.py || true
  python bots/decompose_trigger_v1.py || true
  python bots/status_sync_v1.py || true
  sleep 5
done
