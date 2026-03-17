#!/bin/bash
set -euo pipefail
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export FACTORY_DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OPENAI_MODEL="gpt-5-mini"
export INNOVATION_INSERT_LIMIT="1"
export MERGED_REPROPOSE_HOURS="12"
export CLOSED_REPROPOSE_HOURS="24"
set -a
[ -f env/openai.env ] && source env/openai.env
[ -f env/innovation.env ] && source env/innovation.env
set +a
exec python3 bots/innovation_llm_engine_v1.py
