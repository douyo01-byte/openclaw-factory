#!/usr/bin/env bash
set -euo pipefail
DB="${DB_PATH:?DB_PATH is required}"
proposal_id="${1:?proposal_id required}"
applied_note="${2:-applied to observability runtime live by ceo after planner}"
applied_note_sql=$(python3 - "$applied_note" <<'PY'
import sys
print("'" + sys.argv[1].replace("'", "''") + "'")
PY
)
sqlite3 "$DB" <<SQL
create table if not exists decider_tuning_observability_runtime_live_applied (
  proposal_id integer primary key,
  applied_note text not null,
  applied_at text not null default (datetime('now')),
  source text not null
);
insert into decider_tuning_observability_runtime_live_applied
  (proposal_id, applied_note, applied_at, source)
values
  ($proposal_id, $applied_note_sql, datetime('now'),
   'apply_promoted_tuning_observability_runtime_live.sh')
on conflict(proposal_id) do update set
  applied_note=excluded.applied_note,
  applied_at=datetime('now'),
  source=excluded.source;
update dev_proposals
set guard_status='observability_runtime_live_review_only',
    guard_reason='human_review_observability_runtime_live_applied'
where id=$proposal_id;
SQL
echo "decider_tuning_observability_runtime_live_applied=${proposal_id}"
