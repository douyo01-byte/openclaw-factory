#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

echo '===== approved decision spread ====='
sqlite3 "$DB" "
select coalesce(project_decision,''), count(*)
from dev_proposals
where coalesce(status,'')='approved'
group by coalesce(project_decision,'')
order by count(*) desc;
"

echo
echo '===== approved source spread ====='
sqlite3 "$DB" "
select coalesce(source_ai,''), count(*) total,
       sum(case when coalesce(project_decision,'')='execute_now' then 1 else 0 end) exec_now,
       round(avg(coalesce(priority,0)),4) avg_priority
from dev_proposals
where coalesce(status,'')='approved'
group by coalesce(source_ai,'')
order by total desc;
"

echo
echo '===== cluster bias top ====='
sqlite3 "$DB" "
select source_ai, target_system, improvement_type, success_count, round(bias_score,4)
from cluster_bias
order by bias_score desc, success_count desc
limit 20;
"

echo
echo '===== latest decider dev_events ====='
sqlite3 "$DB" "
select
  proposal_id,
  json_extract(payload,'$.decision') as decision,
  json_extract(payload,'$.priority') as priority,
  json_extract(payload,'$.matched_count') as matched_count,
  json_extract(payload,'$.source_bias') as source_bias,
  json_extract(payload,'$.cluster_bias') as cluster_bias
from dev_events
where event_type='decider_patterns_applied'
order by id desc
limit 20;
"
