#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon
export DB_PATH="${DB_PATH:-/Users/doyopc/AI/openclaw-factory/data/openclaw.db}"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
exec /usr/bin/python3 bots/self_improvement_feedback_metrics_v1.py
