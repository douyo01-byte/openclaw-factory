#!/bin/bash
set -euo pipefail

DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

sqlite3 "$DB" "
insert into inbox_commands(source,text,status,processed,created_at,updated_at)
values
('router_smoke','runtime分類を教えて','pending',0,datetime('now'),datetime('now')),
('router_smoke','本流ボトルネックを教えて','pending',0,datetime('now'),datetime('now')),
('router_smoke','上位3監視ポイントを教えて','pending',0,datetime('now'),datetime('now')),
('router_smoke','[THINK] この本流構成を長文で整理して比較観点も付けて','pending',0,datetime('now'),datetime('now'));
"

sleep 10

echo '===== TASK ROUTER SMOKE ====='
sqlite3 -cmd ".headers on" -cmd ".mode column" "$DB" "
select
  rt.id,
  rt.source_command_id,
  coalesce(rt.target_bot,'') as target_bot,
  coalesce(rt.mode,'') as mode,
  coalesce(rt.status,'') as status,
  substr(coalesce(rt.task_text,''),1,120) as task_text
from router_tasks rt
join inbox_commands ic
  on ic.id = rt.source_command_id
where ic.source='router_smoke'
order by rt.id desc
limit 8;
"

echo
echo '===== TASK ROUTER SMOKE JUDGMENT ====='
sqlite3 "$DB" "
with x as (
  select
    ic.text as text,
    coalesce(rt.target_bot,'') as target_bot,
    coalesce(rt.mode,'') as mode
  from router_tasks rt
  join inbox_commands ic
    on ic.id = rt.source_command_id
  where ic.source='router_smoke'
)
select
  case
    when sum(case when text like '%runtime分類%' and target_bot='kaikun02' and mode='FAST' then 1 else 0 end) >= 1
     and sum(case when text like '%本流ボトルネック%' and target_bot='kaikun02' and mode='FAST' then 1 else 0 end) >= 1
     and sum(case when text like '%上位3監視ポイント%' and target_bot='kaikun02' and mode='FAST' then 1 else 0 end) >= 1
     and sum(case when text like '%[THINK]%' and target_bot='kaikun04' and mode='THINK' then 1 else 0 end) >= 1
    then 'PASS'
    else 'FAIL'
  end;
"
