#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export GITHUB_REPO="douyo01-byte/openclaw-factory"
export GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
export GH_TOKEN="$GITHUB_TOKEN"
exec python -u bots/dev_pr_watcher_v1.py >> logs/jp.openclaw.dev_pr_watcher_v1.out 2>> logs/jp.openclaw.dev_pr_watcher_v1.err
