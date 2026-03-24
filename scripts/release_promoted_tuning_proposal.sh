#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
proposal_id="${1:-}"
release_note="${2:-released manually}"
if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/release_promoted_tuning_proposal.sh <proposal_id> [note]" >&2
  exit 1
fi
note_escaped="$(printf "%s" "$release_note" | sed "s/'/''/g")"
eligible="$(sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_release_plan p on p.proposal_id = dp.id
where dp.id=$proposal_id
  and coalesce(dp.guard_status,'')='promoted_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(p.release_action,'')='ready_for_release';
")"
if [[ "$eligible" != "1" ]]; then
  echo "release_not_applied=$proposal_id"
  exit 1
fi
sqlite3 "$DB" "
create table if not exists decider_tuning_releases(
  proposal_id integer primary key,
  release_note text not null default '',
  released_at text not null default (datetime('now')),
  source text not null default 'release_promoted_tuning_proposal.sh'
);
insert into decider_tuning_releases(
  proposal_id, release_note, released_at, source
) values(
  $proposal_id,
  '$note_escaped',
  datetime('now'),
  'release_promoted_tuning_proposal.sh'
)
on conflict(proposal_id) do update set
  release_note=excluded.release_note,
  released_at=datetime('now'),
  source='release_promoted_tuning_proposal.sh';
update dev_proposals
set
  project_decision='backlog',
  decision_note='human_review_released',
  guard_status='released_review_only',
  guard_reason='decider_tuning_proposal'
where id=$proposal_id;
"
echo "decider_tuning_released=$proposal_id"
