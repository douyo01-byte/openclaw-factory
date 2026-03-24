#!/usr/bin/env bash
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
proposal_id="${1:-}"
note="${2:-applied to normal observability}"
if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/apply_promoted_tuning_normal_observability.sh <proposal_id> [note]" >&2
  exit 1
fi
safe_note=$(printf "%s" "$note" | sed "s/'/''/g")
sqlite3 "$DB" "
create table if not exists decider_tuning_normal_observability_applied(
  proposal_id integer primary key,
  apply_note text not null default '',
  applied_at text not null default '',
  source text not null default ''
);
insert into decider_tuning_normal_observability_applied(
  proposal_id, apply_note, applied_at, source
)
select
  dp.id,
  '$safe_note',
  datetime('now'),
  'apply_promoted_tuning_normal_observability.sh'
from dev_proposals dp
join decider_tuning_normal_observability_plan p on p.proposal_id = dp.id
where dp.id = $proposal_id
  and coalesce(dp.guard_status,'')='normal_merged_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(p.plan_action,'')='ready_for_normal_observability'
on conflict(proposal_id) do update set
  apply_note=excluded.apply_note,
  applied_at=excluded.applied_at,
  source=excluded.source;
update dev_proposals
set
  project_decision='backlog',
  decision_note='human_review_normal_observability_applied',
  guard_status='normal_observability_review_only',
  guard_reason='decider_tuning_proposal'
where id = $proposal_id
  and coalesce(guard_reason,'')='decider_tuning_proposal'
  and exists (
    select 1
    from decider_tuning_normal_observability_plan p
    where p.proposal_id = dev_proposals.id
      and coalesce(p.plan_action,'')='ready_for_normal_observability'
  );
"
echo "decider_tuning_normal_observability_applied=$proposal_id"
