#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon

export DB_PATH=/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db

source .venv/bin/activate

exec python bots/openclaw_supervisor_v1.py
