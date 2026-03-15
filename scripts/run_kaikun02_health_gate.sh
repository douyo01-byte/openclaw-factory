#!/bin/bash
set -euo pipefail
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export DB_PATH="$DB"
export OCLAW_DB_PATH="$DB"
export FACTORY_DB_PATH="$DB"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
/usr/bin/python3 bots/kaikun02_health_gate_v1.py
