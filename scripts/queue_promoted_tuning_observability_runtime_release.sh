#!/usr/bin/env bash
set -euo pipefail
DB="${DB_PATH:?DB_PATH is required}"
proposal_id="${1:?proposal_id required}"
queue_note="${2:-queued for observability runtime release after final gate}"

sqlite3 "$DB" <<SQL
create table if not exists decider_tuning_observability_runtime_release_queue (
  proposal_id integer primary key,
  queue_status text not null,
  queue_note text not null,
  queued_at text not null default (datetime('now')),
  source text not null
);
insert into decider_tuning_observability_runtime_release_queue
  (proposal_id, queue_status, queue_note, queued_at, source)
values
  ($proposal_id, 'queued', $(printf "%Q" "$queue_note"), datetime('now'), 'queue_promoted_tuning_observability_runtime_release.sh')
on conflict(proposal_id) do update set
  queue_status=excluded.queue_status,
  queue_note=excluded.queue_note,
  queued_at=datetime('now'),
  source=excluded.source;
SQL

echo "decider_tuning_observability_runtime_release_queued=${proposal_id}"
