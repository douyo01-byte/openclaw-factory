#!/bin/bash
set -euo pipefail

cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

sqlite3 "$DB" "
insert into inbox_commands(source,text,status,processed,created_at,updated_at)
values
('router_smoke','runtime分 類 を 教 え て ','pending',0,datetime('now'),datetime('now')),
('router_smoke','本 流 ボ ト ル ネ ッ ク を 教 え て ','pending',0,datetime('now'),datetime('now')),
('router_smoke','上 位 3監 視 ポ イ ン ト を 教 え て ','pending',0,datetime('now'),datetime('now')),
('router_smoke','[THINK] こ の 本 流 構 成 を 長文 で 整 理 し て 比 較 観 点 も 付 け て ','pending',0,datetime('now'),datetime('now'));
"

sleep 10

echo '===== TASK ROUTER SMOKE ====='
sqlite3 -cmd ".headers on" -cmd ".mode column" "$DB" "
select
  id,
  source_command_id,
  coalesce(target_bot,'') as target_bot,
  coalesce(mode,'') as mode,
  coalesce(status,'') as status,
  substr(coalesce(task_text,''),1,120) as task_text
from router_tasks
where source_command_id in (
  select id from inbox_commands where source='router_smoke'
)
order by id desc
limit 12;
"

echo '===== TASK ROUTER SMOKE JUDGMENT ====='
sqlite3 "$DB" "
with x as (
  select
    coalesce(ic.text,'') as cmd_text,
    coalesce(rt.target_bot,'') as target_bot,
    coalesce(rt.mode,'') as mode
  from router_tasks rt
  join inbox_commands ic
    on ic.id = rt.source_command_id
  where ic.source='router_smoke'
)
select case
  when sum(case when cmd_text like '%runtime分 類 %' and target_bot='kaikun02' and mode='FAST' then 1 else 0 end) >= 1
   and sum(case when cmd_text like '%本 流 ボ ト ル ネ ッ ク %' and target_bot='kaikun02' and mode='FAST' then 1 else 0 end) >= 1
   and sum(case when cmd_text like '%上 位 3監 視 ポ イ ン ト %' and target_bot='kaikun02' and mode='FAST' then 1 else 0 end) >= 1
   and sum(case when cmd_text like '%[THINK]%' and target_bot='kaikun04' and mode='THINK' then 1 else 0 end) >= 1
  then 'PASS'
  else 'FAIL'
end
from x;
"
