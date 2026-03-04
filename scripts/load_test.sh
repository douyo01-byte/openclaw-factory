#!/usr/bin/env bash
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="$HOME/AI/openclaw-factory-daemon/data/openclaw.db"
export GITHUB_REPO="douyo01-byte/openclaw-factory"
export TELEGRAM_BOT_TOKEN="$(launchctl getenv TELEGRAM_BOT_TOKEN)"
n="${1:-30}"
i=0
t0=$(date +%s)
while [ "$i" -lt "$n" ]; do
  python bots/ingest_telegram_replies_v1.py || true
  python bots/dev_pr_watcher_v1.py || true
  python bots/ci_guard_v1.py || true
  python bots/refiner_guard_v1.py || true
  python bots/decompose_trigger_v1.py || true
  python bots/status_sync_v1.py || true
  i=$((i+1))
done
t1=$(date +%s)
echo "loops=$n sec=$((t1-t0))"
