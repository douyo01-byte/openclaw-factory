#!/bin/bash
set -euo pipefail
DB="${DB_PATH:?DB_PATH is required}"
proposal_id="${1:?proposal_id is required}"
note="${2:-applied to observability core by ceo after planner}"
safe_note=$(printf "%s" "$note" | sed "s/'/''/g")
sqlite3 "$DB" "
create table if not exists decider_tuning_observability_core_applied(
  proposal_id integer primary key,
  apply_note text not null default '',
  applied_at text not null default '',
  source text not null default ''
);
insert into decider_tuning_observability_core_applied(
  proposal_id, apply_note, applied_at, source
)
select
  dp.id,
  '$safe_note',
  datetime('now'),
  'apply_promoted_tuning_observability_core.sh'
from dev_proposals dp
join decider_tuning_observability_core_plan p on p.proposal_id = dp.id
where dp.id = $proposal_id
  and coalesce(dp.guard_status,'')='observability_core_mix_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(p.plan_action,'')='ready_for_observability_core'
on conflict(proposal_id) do update set
  apply_note=excluded.apply_note,
  applied_at=excluded.applied_at,
  source=excluded.source;

update dev_proposals
set project_decision='backlog',
    decision_note='human_review_observability_core_applied',
    guard_status='observability_core_review_only',
    guard_reason='decider_tuning_proposal'
where id = $proposal_id
  and coalesce(guard_status,'')='observability_core_mix_review_only'
  and coalesce(guard_reason,'')='decider_tuning_proposal'
  and exists (
    select 1
    from decider_tuning_observability_core_plan p
    where p.proposal_id = dev_proposals.id
      and coalesce(p.plan_action,'')='ready_for_observability_core'
  );
"
echo "decider_tuning_observability_core_applied=$proposal_id"
