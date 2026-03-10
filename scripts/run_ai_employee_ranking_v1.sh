#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p logs
set -a
source env/telegram_routing.env
set +a
source .venv/bin/activate || exit 1
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
python -u bots/ai_employee_ranking_v1.py >> logs/ai_employee_ranking_v1.out 2>> logs/ai_employee_ranking_v1.err
