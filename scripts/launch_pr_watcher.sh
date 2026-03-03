#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate
echo "[LAUNCH] $(date) bash=$$" >> logs/dev_pr_watcher.out
python3 -u "$PWD/bots/dev_pr_watcher_v1.py" >> logs/dev_pr_watcher.out 2>> logs/dev_pr_watcher.err || true
