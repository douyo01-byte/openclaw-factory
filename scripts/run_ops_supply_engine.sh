#!/bin/bash
cd ~/AI/openclaw-factory-daemon
source .venv/bin/activate
export OCLAW_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
python bots/ops_supply_engine_v1.py
