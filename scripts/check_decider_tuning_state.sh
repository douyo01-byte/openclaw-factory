#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
TEXT_COL="$(sqlite3 "$DB" "
select name
from pragma_table_info('inbox_commands')
where name in ('body','text','command_text','message_text','content','input_text','raw_text','command')
order by case name
  when 'body' then 1
  when 'text' then 2
  when 'command_text' then 3
  when 'message_text' then 4
  when 'content' then 5
  when 'input_text' then 6
  when 'raw_text' then 7
  when 'command' then 8
  else 99
end
limit 1;
")"

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


echo
echo '===== tuning review-only summary ====='
sqlite3 "$DB" "
select
  coalesce(guard_status,'') as guard_status,
  coalesce(decision_note,'') as decision_note,
  coalesce(guard_reason,'') as guard_reason,
  count(*) as cnt
from dev_proposals
where coalesce(title,'') like '[decider-tuning]%'
group by coalesce(guard_status,''), coalesce(decision_note,''), coalesce(guard_reason,'')
order by cnt desc, guard_status asc, decision_note asc, guard_reason asc;
"


echo
echo '===== review-only notification pending count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals
where (
  coalesce(source_ai,'')='decider_threshold_advisor_v1'
  or coalesce(title,'') like '[decider-tuning]%'
)
and coalesce(decision_note,'')='human_review_required'
and coalesce(guard_status,'')='review_only'
and coalesce(guard_reason,'')='decider_tuning_proposal'
and coalesce(notified_at,'')='';
"

echo
echo '===== review-only notification sent count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals
where (
  coalesce(source_ai,'')='decider_threshold_advisor_v1'
  or coalesce(title,'') like '[decider-tuning]%'
)
and coalesce(decision_note,'')='human_review_required'
and coalesce(guard_status,'')='review_only'
and coalesce(guard_reason,'')='decider_tuning_proposal'
and coalesce(notified_at,'')<>'';
"

echo
echo '===== review-only notification latest sent rows ====='
sqlite3 "$DB" "
select
  id,
  coalesce(title,''),
  coalesce(notified_at,''),
  coalesce(notified_msg_id,'')
from dev_proposals
where (
  coalesce(source_ai,'')='decider_threshold_advisor_v1'
  or coalesce(title,'') like '[decider-tuning]%'
)
and coalesce(decision_note,'')='human_review_required'
and coalesce(guard_status,'')='review_only'
and coalesce(guard_reason,'')='decider_tuning_proposal'
and coalesce(notified_at,'')<>''
order by notified_at desc, id desc
limit 20;
"

echo
echo '===== review-only notification state rows ====='
sqlite3 "$DB" "
select
  id,
  coalesce(title,''),
  coalesce(notified_at,''),
  coalesce(notified_msg_id,'')
from dev_proposals
where (
  coalesce(source_ai,'')='decider_threshold_advisor_v1'
  or coalesce(title,'') like '[decider-tuning]%'
)
and coalesce(decision_note,'')='human_review_required'
and coalesce(guard_status,'')='review_only'
and coalesce(guard_reason,'')='decider_tuning_proposal'
order by id desc;
"



echo
echo '===== tuning review decision summary ====='
sqlite3 "$DB" "
select
  coalesce(review_status,'') as review_status,
  count(*) as cnt
from decider_tuning_reviews
group by coalesce(review_status,'')
order by cnt desc, review_status asc;
"

echo
echo '===== tuning latest reviewed rows ====='
sqlite3 "$DB" "
select
  r.proposal_id,
  coalesce(dp.title,''),
  coalesce(r.review_status,''),
  coalesce(r.review_note,''),
  coalesce(r.reviewed_at,''),
  coalesce(r.source,'')
from decider_tuning_reviews r
left join dev_proposals dp on dp.id = r.proposal_id
order by r.reviewed_at desc, r.proposal_id desc
limit 20;
"



echo
echo '===== tuning reply bridge recent inbox ====='
if [ -n "${TEXT_COL:-}" ]; then
sqlite3 "$DB" "
select
  id,
  coalesce(${TEXT_COL},''),
  coalesce(router_status,''),
  coalesce(router_finish_status,''),
  coalesce(router_target,'')
from inbox_commands
where coalesce(router_target,'')='review_only_tuning_reply_bridge_v1'
   or coalesce(${TEXT_COL},'') like 'tune %'
order by id desc
limit 20;
"
else
  echo 'inbox_commands text column not found'
fi
