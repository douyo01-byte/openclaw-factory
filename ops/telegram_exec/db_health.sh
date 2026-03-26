#!/bin/bash
set -euo pipefail
DB="${DB_PATH:-/Users/doyopc/AI/openclaw-factory/data/openclaw.db}"
sqlite3 "$DB" "
select 'kaikun04_done_sent_missing', count(*)
from router_tasks rt
join inbox_commands ic on ic.id = rt.source_command_id
where coalesce(rt.target_bot,'')='kaikun04'
  and coalesce(rt.status,'')='done'
  and coalesce(ic.router_finish_status,'')='sent'
  and coalesce(rt.sent_message_id,'')='';
select 'ops_exec_new_remaining', count(*)
from router_tasks
where coalesce(target_bot,'')='ops_exec'
  and coalesce(status,'')='new';
select 'kaikun02_new_remaining', count(*)
from router_tasks
where coalesce(target_bot,'')='kaikun02'
  and coalesce(status,'')='new';
select 'private_pending', count(*)
from inbox_commands
where coalesce(source,'')='tg_private_chat_log'
  and coalesce(status,'')='pending';
"
