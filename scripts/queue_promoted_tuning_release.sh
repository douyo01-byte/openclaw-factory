#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

proposal_id="${1:-}"
release_note="${2:-}"

if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/queue_promoted_tuning_release.sh <proposal_id> [note]" >&2
  exit 1
fi

note_escaped="$(printf "%s" "$release_note" | sed "s/'/''/g")"

eligible="$(sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_eligibility e on e.proposal_id = dp.id
where dp.id=$proposal_id
  and coalesce(dp.guard_status,'')='promoted_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(e.eligibility_status,'')='eligible';
")"

if [[ "$eligible" != "1" ]]; then
  echo "release_queue_not_applied=$proposal_id"
  exit 1
fi

sqlite3 "$DB" "
create table if not exists decider_tuning_release_queue(
  proposal_id integer primary key,
  release_status text not null,
  release_note text not null default '',
  queued_at text not null default (datetime('now')),
  source text not null default 'queue_promoted_tuning_release.sh'
);
insert into decider_tuning_release_queue(
  proposal_id, release_status, release_note, queued_at, source
) values(
  $proposal_id,
  'queued',
  '$note_escaped',
  datetime('now'),
  'queue_promoted_tuning_release.sh'
)
on conflict(proposal_id) do update set
  release_status='queued',
  release_note=excluded.release_note,
  queued_at=datetime('now'),
  source='queue_promoted_tuning_release.sh';
"

echo "decider_tuning_release_queued=$proposal_id"
