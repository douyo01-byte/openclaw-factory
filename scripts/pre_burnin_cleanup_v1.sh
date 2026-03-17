#!/bin/bash
set -euo pipefail
DB="/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

run_sql() {
  sqlite3 -cmd "pragma busy_timeout=30000" "$DB" "$1"
}

for i in 1 2 3 4 5; do
  if run_sql "
  delete from inbox_commands
  where coalesce(source,'') in ('manual_test','router_smoke');
  "; then
    break
  fi
  sleep 2
done

for i in 1 2 3 4 5; do
  if run_sql "
  update router_tasks
  set status='done',
      finished_at=datetime('now'),
      updated_at=datetime('now'),
      result_text=coalesce(result_text,'') || ' | pre_burnin_cleanup'
  where coalesce(status,'') in ('new','started')
    and (
      coalesce(task_text,'') like '%test fast%'
      or coalesce(task_text,'') like '%runtime分%'
      or coalesce(task_text,'') like '%本 流%'
      or coalesce(task_text,'') like '%監 視%'
    );
  "; then
    break
  fi
  sleep 2
done

run_sql "
select
  coalesce(target_bot,'') as target_bot,
  coalesce(status,'') as status,
  count(*) as cnt
from router_tasks
group by 1,2
order by 1,2;
"
