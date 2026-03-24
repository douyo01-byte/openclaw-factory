#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

echo '===== approved decision spread (normal only) ====='
sqlite3 "$DB" "
select coalesce(project_decision,''), count(*)
from dev_proposals
where coalesce(status,'')='approved'
  and coalesce(source_ai,'') <> 'decider_threshold_advisor_v1'
  and coalesce(title,'') not like '[decider-tuning]%'
  and not (
    coalesce(guard_status,'')='review_only'
    and coalesce(guard_reason,'')='decider_tuning_proposal'
  )
group by coalesce(project_decision,'')
order by count(*) desc;
"

echo
echo '===== approved source spread (normal only) ====='
sqlite3 "$DB" "
select coalesce(source_ai,''), count(*) total,
       sum(case when coalesce(project_decision,'')='execute_now' then 1 else 0 end) exec_now,
       round(avg(coalesce(priority,0)),4) avg_priority
from dev_proposals
where coalesce(status,'')='approved'
  and coalesce(source_ai,'') <> 'decider_threshold_advisor_v1'
  and coalesce(title,'') not like '[decider-tuning]%'
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


echo
echo '===== decider feedback summary ====='
sqlite3 "$DB" "
select
  coalesce(source_ai,'') as source_ai,
  coalesce(decision,'') as decision,
  coalesce(matched_band,'') as matched_band,
  sample_count,
  round(avg_source_bias,4),
  round(avg_cluster_bias,4)
from decider_feedback_metrics
order by sample_count desc, source_ai asc, decision asc, matched_band asc
limit 30;
"

echo
echo '===== latest-only old payload count ====='
sqlite3 "$DB" "
with latest as (
  select proposal_id, max(id) as max_id
  from dev_events
  where event_type='decider_patterns_applied'
  group by proposal_id
)
select count(*)
from latest l
join dev_events de on de.id = l.max_id
where json_extract(de.payload,'$.matched_count') is null
   or coalesce(json_extract(de.payload,'$.matched_count'),0) <= 0;
"


echo
echo '===== tuning proposal spread ====='
sqlite3 "$DB" "
select coalesce(project_decision,''), count(*)
from dev_proposals
where coalesce(status,'')='approved'
  and (
    coalesce(source_ai,'')='decider_threshold_advisor_v1'
    or coalesce(title,'') like '[decider-tuning]%'
    or (
      coalesce(guard_status,'')='review_only'
      and coalesce(guard_reason,'')='decider_tuning_proposal'
    )
  )
group by coalesce(project_decision,'')
order by count(*) desc;
"

echo
echo '===== tuning proposal source spread ====='
sqlite3 "$DB" "
select coalesce(source_ai,''), count(*) total,
       sum(case when coalesce(project_decision,'')='execute_now' then 1 else 0 end) exec_now,
       round(avg(coalesce(priority,0)),4) avg_priority
from dev_proposals
where coalesce(status,'')='approved'
  and (
    coalesce(source_ai,'')='decider_threshold_advisor_v1'
    or coalesce(title,'') like '[decider-tuning]%'
  )
group by coalesce(source_ai,'')
order by total desc;
"
