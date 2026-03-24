#!/usr/bin/env bash
set -euo pipefail
DB="${DB_PATH:-${1:-}}"
proposal_id="${1:-}"
note="${2:-queued for observability core after final gate}"
[ -n "$proposal_id" ] || { echo "usage: $0 <proposal_id> [note]" >&2; exit 1; }
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
safe_note=$(printf "%s" "$note" | sed "s/'/''/g")
sqlite3 "$DB" "
create table if not exists decider_tuning_observability_core_queue(
  proposal_id integer primary key,
  queue_status text not null default '',
  queue_note text not null default '',
  queued_at text not null default '',
  source text not null default ''
);
insert into decider_tuning_observability_core_queue(
  proposal_id, queue_status, queue_note, queued_at, source
)
select
  dp.id,
  'queued',
  '$safe_note',
  datetime('now'),
  'queue_promoted_tuning_observability_core.sh'
from dev_proposals dp
join decider_tuning_observability_core_final_gate g on g.proposal_id = dp.id
where dp.id = $proposal_id
  and coalesce(dp.guard_status,'')='observability_core_mix_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(g.gate_status,'')='open_for_observability_core'
on conflict(proposal_id) do update set
  queue_status=excluded.queue_status,
  queue_note=excluded.queue_note,
  queued_at=excluded.queued_at,
  source=excluded.source;
"
echo "decider_tuning_observability_core_queued=$proposal_id"
