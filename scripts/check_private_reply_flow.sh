#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
u=$(id -u)

echo '===== LAUNCHCTL ====='
launchctl print "gui/$u/jp.openclaw.ingest_private_replies_kaikun04" 2>/dev/null | egrep 'state =|pid =|last exit code =' || true
launchctl print "gui/$u/jp.openclaw.private_reply_to_inbox_v1" 2>/dev/null | egrep 'state =|pid =|last exit code =' || true
launchctl print "gui/$u/jp.openclaw.secretary_llm_v1" 2>/dev/null | egrep 'state =|pid =|last exit code =' || true
echo

echo '===== PENDING ====='
sqlite3 "$DB" "
select
  count(*) as pending_total
from inbox_commands
where coalesce(source,'')='tg_private_chat_log'
  and coalesce(status,'')='pending';
"
echo

echo '===== PENDING_OLDER_THAN_5M ====='
sqlite3 "$DB" "
select
  count(*) as older_than_5m
from inbox_commands
where coalesce(source,'')='tg_private_chat_log'
  and coalesce(status,'')='pending'
  and created_at < datetime('now','-5 minutes');
"
echo

echo '===== RECENT INBOX ====='
sqlite3 "$DB" "
select id, router_mode, status, substr(coalesce(text,''),1,100), created_at
from inbox_commands
where coalesce(source,'')='tg_private_chat_log'
order by id desc
limit 10;
"
echo

echo '===== RECENT INGEST ====='
sqlite3 "$DB" "
select id, substr(coalesce(text,''),1,100), coalesce(router_ingested,''), created_at
from tg_private_chat_log
order by id desc
limit 10;
"
echo

echo '===== 24H SUMMARY ====='
sqlite3 "$DB" "
select
  sum(case when coalesce(router_ingested,'')='yes' then 1 else 0 end) as yes_count,
  sum(case when coalesce(router_ingested,'')='skipped_noise' then 1 else 0 end) as skipped_noise_count,
  sum(case when coalesce(router_ingested,'')='skipped_dup' then 1 else 0 end) as skipped_dup_count
from tg_private_chat_log
where created_at >= datetime('now','-1 day');
"
