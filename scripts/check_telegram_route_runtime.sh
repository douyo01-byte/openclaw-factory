#!/bin/bash
set -euo pipefail
u=$(id -u)
DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

echo '===== PRIMARY ====='
for label in \
  jp.openclaw.api_server \
  jp.openclaw.task_router_v1 \
  jp.openclaw.kaikun04_router_worker_v1 \
  jp.openclaw.telegram_ops_executor_v1 \
  jp.openclaw.router_reply_finisher_v1
do
  echo "----- $label -----"
  launchctl print "gui/$u/$label" 2>/dev/null | egrep 'state =|pid =|last exit code =|program =|path ='
done

echo
echo '===== FALLBACK ====='
for label in \
  jp.openclaw.private_reply_to_inbox_v1 \
  jp.openclaw.ingest_private_replies_kaikun04 \
  jp.openclaw.secretary_llm_v1
do
  echo "----- $label -----"
  launchctl print "gui/$u/$label" 2>/dev/null | egrep 'state =|pid =|last exit code =|program =|path ='
done

echo
echo '===== RECENT PRIMARY SOURCES ====='
sqlite3 "$DB_PATH" "
select id,source,text,status,router_status,router_target,router_finish_status,router_task_id,created_at
from inbox_commands
where source in ('telegram_n8n','telegram_primary','n8n')
order by id desc
limit 12;
"

echo
echo '===== RECENT FALLBACK SOURCES ====='
sqlite3 "$DB_PATH" "
select id,source,text,status,router_status,router_target,router_finish_status,router_task_id,created_at
from inbox_commands
where source in ('tg_private_chat_log','private_reply_bridge','manual')
order by id desc
limit 12;
"
