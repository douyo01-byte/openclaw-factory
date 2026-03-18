#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1

set -a
[ -f env/common.env ] && source env/common.env
[ -f env/openai.env ] && source env/openai.env
set +a

DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export DB_PATH="$DB"
export OCLAW_DB_PATH="$DB"
export FACTORY_DB_PATH="$DB"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
export OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o-mini}"

exec /Users/doyopc/AI/openclaw-factory-daemon/.venv/bin/python -u bots/spec_refiner_v2.py >> logs/spec_refiner_v2.out 2>> logs/spec_refiner_v2.err
