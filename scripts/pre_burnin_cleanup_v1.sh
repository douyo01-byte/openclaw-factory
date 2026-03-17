#!/bin/bash
set -euo pipefail
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

sqlite3 "$DB" "
delete from inbox_commands
where coalesce(source,'') in ('manual_test','router_smoke');
"

sqlite3 "$DB" "
update router_tasks
set status='done',
    finished_at=datetime('now'),
    updated_at=datetime('now'),
    result_text=coalesce(result_text,'') || ' | pre_burnin_cleanup'
where coalesce(status,'') in ('new','started')
  and (
    coalesce(task_text,'') like '%runtime分%'
    or coalesce(task_text,'') like '%本 流%'
    or coalesce(task_text,'') like '%監 視%'
    or coalesce(task_text,'') like '%test fast%'
  );
"

sqlite3 -cmd '.headers on' -cmd '.mode column' "$DB" "
select
  coalesce(target_bot,'') as target_bot,
  coalesce(status,'') as status,
  count(*) as cnt
from router_tasks
group by 1,2
order by 1,2;
"
