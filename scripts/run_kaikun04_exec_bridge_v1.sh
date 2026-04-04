#!/bin/bash
cd ~/AI/openclaw-factory-daemon || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
python3 bots/kaikun04_exec_bridge_v1.py
