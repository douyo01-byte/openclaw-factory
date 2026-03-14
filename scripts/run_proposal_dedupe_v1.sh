#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/proposal_dedupe_v1.py
