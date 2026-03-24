#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
proposal_id="${1:-}"
note="${2:-queued for normal merge}"
if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/queue_promoted_tuning_normal_merge.sh <proposal_id> [note]" >&2
  exit 1
fi

sqlite3 "$DB" "
create table if not exists decider_tuning_normal_merge_queue(
  proposal_id integer primary key,
  queue_status text not null default '',
  queue_note text not null default '',
  queued_at text not null default (datetime('now')),
  source text not null default 'queue_promoted_tuning_normal_merge.sh'
);

with target as (
  select dp.id
  from dev_proposals dp
  join decider_tuning_normalization_gate g on g.proposal_id = dp.id
  where dp.id = ${proposal_id}
    and coalesce(dp.guard_status,'')='normalized_review_only'
    and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    and coalesce(g.gate_status,'')='open_for_normal_merge'
)
insert into decider_tuning_normal_merge_queue(
  proposal_id, queue_status, queue_note, queued_at, source
)
select
  id,
  'queued',
  replace('${note}', '''', ''''''),
  datetime('now'),
  'queue_promoted_tuning_normal_merge.sh'
from target
on conflict(proposal_id) do update set
  queue_status='queued',
  queue_note=excluded.queue_note,
  queued_at=datetime('now'),
  source='queue_promoted_tuning_normal_merge.sh';
"

echo "decider_tuning_normal_merge_queued=${proposal_id}"
