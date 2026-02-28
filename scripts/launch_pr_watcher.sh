#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory
export PATH="/opt/homebrew/bin:/usr/bin:/bin"
export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory
set -a
source .env.openclaw
exec /bin/bash -lc "source .venv/bin/activate && python bots/dev_pr_watcher_v1.py"
