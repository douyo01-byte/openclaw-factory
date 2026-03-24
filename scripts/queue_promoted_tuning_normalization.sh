#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
proposal_id="${1:-}"
queue_note="${2:-queued_for_normalization}"
if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/queue_promoted_tuning_normalization.sh <proposal_id> [note]" >&2
  exit 1
fi
note_escaped="$(printf "%s" "$queue_note" | sed "s/'/''/g")"
sqlite3 "$DB" "
create table if not exists decider_tuning_normalization_queue(
  proposal_id integer primary key,
  queue_status text not null,
  queue_note text not null default '',
  queued_at text not null default (datetime('now')),
  source text not null default 'queue_promoted_tuning_normalization.sh'
);
insert or replace into decider_tuning_normalization_queue(
  proposal_id, queue_status, queue_note, queued_at, source
)
select
  dp.id,
  'queued',
  '$note_escaped',
  datetime('now'),
  'queue_promoted_tuning_normalization.sh'
from dev_proposals dp
join decider_tuning_release_gate g on g.proposal_id = dp.id
where dp.id=$proposal_id
  and coalesce(dp.guard_status,'')='released_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(g.gate_status,'')='open_for_normalization';
"
if ! sqlite3 "$DB" "select 1 from decider_tuning_normalization_queue where proposal_id=$proposal_id;" | grep -q 1; then
  echo "decider_tuning_normalization_queue_not_applied=$proposal_id"
  exit 1
fi
echo "decider_tuning_normalization_queued=$proposal_id"
