#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export PYTHONPATH=$PWD
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
exec /usr/bin/python3 bots/ceo_terminal_executor_guarded_normalizer_v1.py
