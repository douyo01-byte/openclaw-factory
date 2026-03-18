#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
python3 bots/ceo_terminal_guard_bridge_v1.py
