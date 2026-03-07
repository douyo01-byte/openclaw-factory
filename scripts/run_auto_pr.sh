#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory || exit 1
source /Users/doyopc/AI/openclaw-factory/.venv/bin/activate || exit 1
set -a
source /Users/doyopc/AI/openclaw-factory/env/openai.env
source /Users/doyopc/AI/openclaw-factory/env/github.env
set +a
export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
exec python -u /Users/doyopc/AI/openclaw-factory/bots/auto_pr_v1.py
