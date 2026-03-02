#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export GITHUB_REPO="douyo01-byte/openclaw-factory"
while true; do
  python bots/dev_pr_watcher_v1.py || true
  sleep 5
done
