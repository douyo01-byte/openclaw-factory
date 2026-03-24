#!/bin/bash
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
proposal_id="${1:-}"
note="${2:-applied to observability core mix by ceo after planner}"
if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/apply_promoted_tuning_observability_core_mix.sh <proposal_id> [note]" >&2
  exit 1
fi
safe_note=$(printf "%s" "$note" | sed "s/'/''/g")
sqlite3 "$DB" "
create table if not exists decider_tuning_observability_core_mix_applied(
  proposal_id integer primary key,
  apply_note text not null default '',
  applied_at text not null default '',
  source text not null default ''
);
insert into decider_tuning_observability_core_mix_applied(
  proposal_id, apply_note, applied_at, source
)
select
  dp.id,
  '$safe_note',
  datetime('now'),
  'apply_promoted_tuning_observability_core_mix.sh'
from dev_proposals dp
join decider_tuning_observability_core_mix_plan p on p.proposal_id = dp.id
where dp.id = $proposal_id
  and coalesce(dp.guard_status,'')='normal_observability_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(p.mix_action,'')='ready_for_observability_core_mix'
on conflict(proposal_id) do update set
  apply_note=excluded.apply_note,
  applied_at=excluded.applied_at,
  source=excluded.source;
update dev_proposals
set
  project_decision='backlog',
  decision_note='human_review_observability_core_mix_applied',
  guard_status='observability_core_mix_review_only',
  guard_reason='decider_tuning_proposal'
where id = $proposal_id
  and coalesce(guard_reason,'')='decider_tuning_proposal';
"
echo "decider_tuning_observability_core_mix_applied=$proposal_id"
