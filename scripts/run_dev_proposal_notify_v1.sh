#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-daemon
source .venv/bin/activate

set -a
[ -f env/openai.env ] && source env/openai.env
[ -f env/telegram.env ] && source env/telegram.env
set +a

export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"

exec python -u -m bots.dev_proposal_notify_v1 >> logs/dev_proposal_notify_v1.out 2>> logs/dev_proposal_notify_v1.err
