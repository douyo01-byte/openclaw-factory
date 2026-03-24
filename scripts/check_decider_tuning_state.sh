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
echo '===== approved but not promoted count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_reviews r on r.proposal_id = dp.id
left join decider_tuning_promotions p on p.proposal_id = dp.id
where (
  coalesce(dp.source_ai,'')='decider_threshold_advisor_v1'
  or coalesce(dp.title,'') like '[decider-tuning]%'
)
and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
and coalesce(r.review_status,'')='approved'
and p.proposal_id is null;
"

echo
echo '===== promoted summary ====='
sqlite3 "$DB" "
select
  coalesce(dp.guard_status,'') as guard_status,
  coalesce(dp.decision_note,'') as decision_note,
  count(*) as cnt
from decider_tuning_promotions p
join dev_proposals dp on dp.id = p.proposal_id
group by coalesce(dp.guard_status,''), coalesce(dp.decision_note,'')
order by cnt desc, guard_status asc, decision_note asc;
"

echo
echo '===== promoted latest rows ====='
sqlite3 "$DB" "
select
  p.proposal_id,
  coalesce(dp.title,''),
  coalesce(dp.project_decision,''),
  coalesce(dp.guard_status,''),
  coalesce(dp.decision_note,''),
  coalesce(p.promotion_note,''),
  coalesce(p.promoted_at,''),
  coalesce(p.source,'')
from decider_tuning_promotions p
join dev_proposals dp on dp.id = p.proposal_id
order by p.promoted_at desc, p.proposal_id desc
limit 20;
"

echo
echo '===== promoted notification pending count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals
where coalesce(guard_status,'')='promoted_review_only'
  and coalesce(guard_reason,'')='decider_tuning_proposal'
  and coalesce(promoted_notified_at,'')='';
"

echo
echo '===== promoted notification sent count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals
where coalesce(guard_status,'')='promoted_review_only'
  and coalesce(guard_reason,'')='decider_tuning_proposal'
  and coalesce(promoted_notified_at,'')<>'';
"

echo
echo '===== promoted notification latest sent rows ====='
sqlite3 "$DB" "
select
  id,
  coalesce(title,''),
  coalesce(promoted_notified_at,''),
  coalesce(promoted_notified_msg_id,'')
from dev_proposals
where coalesce(guard_status,'')='promoted_review_only'
  and coalesce(guard_reason,'')='decider_tuning_proposal'
  and coalesce(promoted_notified_at,'')<>''
order by promoted_notified_at desc, id desc
limit 20;
"


echo
echo '===== release queue summary ====='
sqlite3 "$DB" "
select
  coalesce(release_status,'') as release_status,
  count(*) as cnt
from decider_tuning_release_queue
group by coalesce(release_status,'')
order by cnt desc, release_status asc;
"

echo
echo '===== eligible but not queued count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_eligibility e on e.proposal_id = dp.id
left join decider_tuning_release_queue q on q.proposal_id = dp.id
where coalesce(dp.guard_status,'')='promoted_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(e.eligibility_status,'')='eligible'
  and q.proposal_id is null;
"

echo
echo '===== queued latest rows ====='
sqlite3 "$DB" "
select
  q.proposal_id,
  coalesce(dp.title,''),
  coalesce(q.release_status,''),
  coalesce(q.release_note,''),
  coalesce(q.queued_at,''),
  coalesce(q.source,'')
from decider_tuning_release_queue q
join dev_proposals dp on dp.id = q.proposal_id
order by q.queued_at desc, q.proposal_id desc
limit 20;
"


echo
echo '===== release planner summary ====='
sqlite3 "$DB" "
select
  coalesce(release_action,'') as release_action,
  coalesce(release_reason,'') as release_reason,
  count(*) as cnt
from decider_tuning_release_plan
group by coalesce(release_action,''), coalesce(release_reason,'')
order by cnt desc, release_action asc, release_reason asc;
"

echo
echo '===== ready but not released count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_release_plan p on p.proposal_id = dp.id
where coalesce(dp.guard_status,'')='promoted_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(p.release_action,'')='ready_for_release';
"

echo
echo '===== latest release plan rows ====='
sqlite3 "$DB" "
select
  p.proposal_id,
  coalesce(dp.title,''),
  coalesce(p.release_action,''),
  coalesce(p.release_reason,''),
  coalesce(p.planned_at,''),
  coalesce(p.source,'')
from decider_tuning_release_plan p
join dev_proposals dp on dp.id = p.proposal_id
order by p.planned_at desc, p.proposal_id desc
limit 20;
"


echo
echo '===== release applied summary ====='
sqlite3 "$DB" "
select
  coalesce(dp.guard_status,'') as guard_status,
  coalesce(dp.decision_note,'') as decision_note,
  count(*) as cnt
from decider_tuning_releases r
join dev_proposals dp on dp.id = r.proposal_id
group by coalesce(dp.guard_status,''), coalesce(dp.decision_note,'')
order by cnt desc, guard_status asc, decision_note asc;
"

echo
echo '===== ready but not applied count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_release_plan p on p.proposal_id = dp.id
left join decider_tuning_releases r on r.proposal_id = dp.id
where coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(p.release_action,'')='ready_for_release'
  and r.proposal_id is null;
"

echo
echo '===== latest released rows ====='
sqlite3 "$DB" "
select
  r.proposal_id,
  coalesce(dp.title,''),
  coalesce(dp.project_decision,''),
  coalesce(dp.guard_status,''),
  coalesce(dp.decision_note,''),
  coalesce(r.release_note,''),
  coalesce(r.released_at,''),
  coalesce(r.source,'')
from decider_tuning_releases r
join dev_proposals dp on dp.id = r.proposal_id
order by r.released_at desc, r.proposal_id desc
limit 20;
"


echo
echo '===== release gate summary ====='
sqlite3 "$DB" "
select
  coalesce(gate_status,'') as gate_status,
  coalesce(gate_reason,'') as gate_reason,
  count(*) as cnt
from decider_tuning_release_gate
group by coalesce(gate_status,''), coalesce(gate_reason,'')
order by cnt desc, gate_status asc, gate_reason asc;
"

echo
echo '===== open for normalization count ====='
sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_release_gate g on g.proposal_id = dp.id
where coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(g.gate_status,'')='open_for_normalization';
"

echo
echo '===== latest release gate rows ====='
sqlite3 "$DB" "
select
  g.proposal_id,
  coalesce(dp.title,''),
  coalesce(dp.project_decision,''),
  coalesce(dp.guard_status,''),
  coalesce(dp.decision_note,''),
  coalesce(g.gate_status,''),
  coalesce(g.gate_reason,''),
  coalesce(g.checked_at,''),
  coalesce(g.source,'')
from decider_tuning_release_gate g
join dev_proposals dp on dp.id = g.proposal_id
order by g.checked_at desc, g.proposal_id desc
limit 20;
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
echo '===== tuning reply bridge status summary ====='
sqlite3 "$DB" "
select
  coalesce(router_status,'') as router_status,
  coalesce(router_finish_status,'') as router_finish_status,
  count(*) as cnt
from inbox_commands
where coalesce(router_target,'')='review_only_tuning_reply_bridge_v1'
group by coalesce(router_status,''), coalesce(router_finish_status,'')
order by cnt desc, router_status asc, router_finish_status asc;
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



echo
echo '===== review-only isolated state ====='
sqlite3 "$DB" "
select
  sum(case
    when (
      coalesce(source_ai,'')='decider_threshold_advisor_v1'
      or coalesce(title,'') like '[decider-tuning]%'
      or (
        coalesce(guard_status,'')='review_only'
        and coalesce(guard_reason,'')='decider_tuning_proposal'
      )
    ) then 1 else 0 end) as isolated_review_only_count,
  sum(case
    when (
      coalesce(source_ai,'')='decider_threshold_advisor_v1'
      or coalesce(title,'') like '[decider-tuning]%'
      or (
        coalesce(guard_status,'')='review_only'
        and coalesce(guard_reason,'')='decider_tuning_proposal'
      )
    )
    and coalesce(project_decision,'')='execute_now'
    then 1 else 0 end) as leaked_execute_now_count
from dev_proposals
where coalesce(status,'')='approved';
"

echo
echo '===== review-only learning leak count ====='
sqlite3 "$DB" "
select count(*)
from decider_feedback_metrics
where coalesce(source_ai,'')='decider_threshold_advisor_v1';
"

echo
echo '===== review-only latest decider events ====='
sqlite3 "$DB" "
with latest as (
  select proposal_id, max(id) as max_id
  from dev_events
  where event_type='decider_patterns_applied'
  group by proposal_id
)
select
  dp.id,
  coalesce(dp.title,''),
  coalesce(json_extract(de.payload,'$.decision'),''),
  coalesce(json_extract(de.payload,'$.matched_count'),''),
  round(coalesce(json_extract(de.payload,'$.source_bias'),0),4),
  round(coalesce(json_extract(de.payload,'$.cluster_bias'),0),4)
from latest l
join dev_events de on de.id = l.max_id
left join dev_proposals dp on dp.id = de.proposal_id
where
  coalesce(dp.source_ai,'')='decider_threshold_advisor_v1'
  or coalesce(dp.title,'') like '[decider-tuning]%'
  or (
    coalesce(dp.guard_status,'')='review_only'
    and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  )
order by dp.id desc
limit 20;
"
