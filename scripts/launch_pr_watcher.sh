#!/usr/bin/env bash
cd /Users/doyopc/AI/openclaw-factory
source .venv/bin/activate
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory
python bots/dev_pr_watcher_v1.py >> logs/dev_pr_watcher.out 2>> logs/dev_pr_watcher.err
