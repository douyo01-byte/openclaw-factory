#!/bin/bash
set -euo pipefail

cd ~/AI/openclaw-factory-daemon || exit 1
source .venv/bin/activate || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

if [ $# -lt 4 ]; then
  echo "usage: run_lp_sales_pipeline.sh <job_id> <version> <template_html> <json_input>"
  exit 1
fi

JOB_ID="$1"
VERSION="$2"
TEMPLATE="$3"
JSON_INPUT="$4"
OUT_HTML="data/telegram_os_html/job_${JOB_ID}_lp_v${VERSION}.html"
TITLE="lp_html_export_v${VERSION}_manual"

python scripts/check_lp_json_placeholders.py "$JSON_INPUT"
python scripts/render_lp_sales_template.py --json "$TEMPLATE" "$JSON_INPUT" "$OUT_HTML"
./scripts/check_lp_output.sh "$OUT_HTML"

python bots/lp_sales_manual_publish_worker.py "$JOB_ID" "$VERSION" "$OUT_HTML" "lp_html_export_v3" "$TITLE"

python bots/public_preview_publish_worker_v1.py

sqlite3 "$DB_PATH" "
delete from conversation_outbox where job_id=${JOB_ID};
update conversation_jobs
set final_reply_text='',
    final_reply_status='',
    updated_at=datetime('now')
where id=${JOB_ID};
"

python bots/conversation_reply_persist_v1.py
python bots/conversation_reply_to_outbox_v1.py
./scripts/run_conversation_outbox_sender_v1.sh

echo '----- JOB -----'
sqlite3 "$DB_PATH" "
select id,current_phase,status,final_reply_status
from conversation_jobs
where id=${JOB_ID};
"

echo '----- HTML -----'
sqlite3 "$DB_PATH" "
select id,artifact_type,artifact_title,artifact_path,version
from conversation_artifacts
where job_id=${JOB_ID}
  and artifact_type like 'lp_html_export%'
order by id desc
limit 5;
"

echo '----- PREVIEW -----'
sqlite3 "$DB_PATH" "
select id,artifact_type,artifact_body,version
from conversation_artifacts
where job_id=${JOB_ID}
  and artifact_type='public_preview_url'
order by id desc
limit 3;
"

echo '----- OUTBOX -----'
sqlite3 "$DB_PATH" "
select id,job_id,chat_id,status,sent_message_id
from conversation_outbox
where job_id=${JOB_ID}
order by id desc
limit 5;
"
