#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

echo '===== decider threshold advice ====='
sqlite3 "$DB" "
select
  coalesce(source_ai,''),
  coalesce(decision,''),
  coalesce(matched_band,''),
  sample_count,
  round(avg_source_bias,4),
  round(avg_cluster_bias,4),
  coalesce(suggested_action,''),
  coalesce(suggestion_reason,'')
from decider_threshold_advice
order by sample_count desc, source_ai asc, decision asc, matched_band asc;
"

echo
echo '===== tuning proposals ====='
sqlite3 "$DB" "
select
  id,
  coalesce(source_ai,''),
  coalesce(branch_name,''),
  coalesce(title,''),
  coalesce(status,''),
  coalesce(project_decision,''),
  coalesce(priority,0)
from dev_proposals
where coalesce(title,'') like '[decider-tuning]%'
order by id desc
limit 30;
"

echo
echo '===== tuning proposal registry ====='
sqlite3 "$DB" "
select
  coalesce(source_ai,''),
  coalesce(decision,''),
  coalesce(matched_band,''),
  proposal_id,
  coalesce(created_at,'')
from decider_tuning_proposals
order by created_at desc, proposal_id desc;
"

echo
echo '===== tuning duplicate check ====='
sqlite3 "$DB" "
select
  coalesce(source_ai,''),
  coalesce(decision,''),
  coalesce(matched_band,''),
  count(*) as cnt,
  min(proposal_id) as min_proposal_id,
  max(proposal_id) as max_proposal_id,
  max(coalesce(created_at,'')) as latest_created_at
from decider_tuning_proposals
group by coalesce(source_ai,''), coalesce(decision,''), coalesce(matched_band,'')
order by cnt desc, source_ai asc, decision asc, matched_band asc;
"

echo
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
select
  coalesce(source_ai,''),
  count(*) total,
  sum(case when coalesce(project_decision,'')='execute_now' then 1 else 0 end) exec_now,
  round(avg(coalesce(priority,0)),4) avg_priority
from dev_proposals
where coalesce(status,'')='approved'
group by coalesce(source_ai,'')
order by total desc;
"


echo
echo '===== tuning proposal summary ====='
sqlite3 "$DB" "
select
  count(*) as proposal_count,
  max(coalesce(created_at,'')) as latest_created_at
from decider_tuning_proposals;
"

echo
echo '===== tuning proposal status summary ====='
sqlite3 "$DB" "
select
  coalesce(dp.project_decision,'') as project_decision,
  count(*) as cnt
from decider_tuning_proposals r
join dev_proposals dp on dp.id = r.proposal_id
group by coalesce(dp.project_decision,'')
order by cnt desc, project_decision asc;
"
