#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
set -a
source /Users/doyopc/AI/openclaw-factory-daemon/env/openai.env
set +a
export DB_PATH="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$DB_PATH"
export FACTORY_DB_PATH="$DB_PATH"
export PYTHONPATH="/Users/doyopc/AI/openclaw-factory-daemon"
python - <<'PY'
import os
v=os.environ.get("OPENAI_API_KEY","")
print("OPENAI_API_KEY_LEN=", len(v), flush=True)
print("OPENAI_API_KEY_PREFIX=", v[:7] if v else "", flush=True)
PY
exec python -u -m bots.innovation_llm_engine_v1 >> logs/innovation_llm_engine_v1.out 2>> logs/innovation_llm_engine_v1.err
