#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export PYTHONPATH=$PWD
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
./.venv/bin/python bots/ceo_terminal_guard_selector_v1.py
