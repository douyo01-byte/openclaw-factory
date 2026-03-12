#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export GITHUB_REPO="douyo01-byte/openclaw-factory"
exec python -u bots/dev_pr_creator_v1.py >> logs/dev_pr_creator_v1.out 2>> logs/dev_pr_creator_v1.err
