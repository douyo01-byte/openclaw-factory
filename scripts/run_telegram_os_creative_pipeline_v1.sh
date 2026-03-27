#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

python3 bots/inbox_to_conversation_jobs_v1.py
python3 bots/creative_analysis_worker_v2.py
python3 bots/lp_variant_reviewer_v1.py
python3 bots/lp_variant_improver_v1.py
python3 bots/image_plan_worker_v1.py
python3 bots/product_image_url_worker_v1.py
python3 bots/fv_wireframe_worker_v1.py
python3 bots/section_outline_worker_v1.py
python3 bots/fv_copy_final_worker_v1.py
python3 bots/conversation_reply_persist_v1.py
python3 bots/conversation_reply_to_outbox_v1.py
