#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory
export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory
set -a
source /Users/doyopc/AI/openclaw-factory/.env.openclaw
exec /Users/doyopc/AI/openclaw-factory/.venv/bin/python /Users/doyopc/AI/openclaw-factory/bots/dev_executor_v1.py
