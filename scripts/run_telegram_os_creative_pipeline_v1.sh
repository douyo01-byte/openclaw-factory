#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

python3 bots/inbox_to_conversation_jobs_v1.py
python3 bots/creative_analysis_worker_v2.py
python3 bots/lp_variant_reviewer_v1.py
python3 bots/lp_variant_improver_v1.py
python3 bots/conversation_reply_persist_v1.py
