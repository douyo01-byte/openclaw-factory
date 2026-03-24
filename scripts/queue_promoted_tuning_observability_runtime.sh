#!/usr/bin/env bash
set -euo pipefail

DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
proposal_id="${1:?proposal_id required}"
note="${2:-queued for observability runtime after gate}"

sqlite3 "$DB" <<SQL
create table if not exists decider_tuning_observability_runtime_queue (
  proposal_id integer primary key,
  queue_status text not null,
  queue_note text,
  queued_at text not null default (datetime('now')),
  source text not null
);

insert into decider_tuning_observability_runtime_queue (
  proposal_id, queue_status, queue_note, queued_at, source
)
select
  dp.id,
  'queued',
  '$note',
  datetime('now'),
  'queue_promoted_tuning_observability_runtime.sh'
from dev_proposals dp
join decider_tuning_observability_runtime_gate g on g.proposal_id = dp.id
where dp.id = $proposal_id
  and coalesce(dp.guard_status,'')='observability_core_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(g.gate_status,'')='open_for_observability_runtime'
on conflict(proposal_id) do update set
  queue_status=excluded.queue_status,
  queue_note=excluded.queue_note,
  queued_at=excluded.queued_at,
  source=excluded.source;
SQL

echo "decider_tuning_observability_runtime_queued=$proposal_id"
