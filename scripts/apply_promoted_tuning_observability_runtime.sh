#!/usr/bin/env bash
set -euo pipefail

DB="${DB_PATH:?DB_PATH is required}"
proposal_id="${1:?proposal_id required}"
applied_note="${2:-applied to observability runtime by ceo after planner}"

sqlite3 "$DB" <<SQL
create table if not exists decider_tuning_observability_runtime_applied (
  proposal_id integer primary key,
  applied_guard_status text not null,
  applied_guard_reason text not null,
  applied_note text not null,
  applied_at text not null default (datetime('now')),
  source text not null
);

update dev_proposals
set guard_status='observability_runtime_review_only',
    guard_reason='human_review_observability_runtime_applied'
where id=${proposal_id}
  and coalesce(guard_reason,'')='decider_tuning_proposal';

insert into decider_tuning_observability_runtime_applied (
  proposal_id, applied_guard_status, applied_guard_reason, applied_note, applied_at, source
) values (
  ${proposal_id},
  'observability_runtime_review_only',
  'human_review_observability_runtime_applied',
  '$(printf "%s" "$applied_note" | sed "s/'/''/g")',
  datetime('now'),
  'apply_promoted_tuning_observability_runtime.sh'
)
on conflict(proposal_id) do update set
  applied_guard_status=excluded.applied_guard_status,
  applied_guard_reason=excluded.applied_guard_reason,
  applied_note=excluded.applied_note,
  applied_at=datetime('now'),
  source=excluded.source;
SQL

echo "decider_tuning_observability_runtime_applied=${proposal_id}"
