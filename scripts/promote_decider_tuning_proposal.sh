#!/bin/zsh
set -euo pipefail

cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

proposal_id="${1:-}"
promotion_note="${2:-}"

if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/promote_decider_tuning_proposal.sh <proposal_id> [note]" >&2
  exit 1
fi

note_escaped="$(printf "%s" "$promotion_note" | sed "s/'/''/g")"

sqlite3 "$DB" "
create table if not exists decider_tuning_promotions(
  proposal_id integer primary key,
  promotion_note text not null default '',
  promoted_at text not null default (datetime('now')),
  source text not null default 'promote_decider_tuning_proposal.sh'
);
"

eligible="$(sqlite3 "$DB" "
select count(*)
from dev_proposals dp
join decider_tuning_reviews r on r.proposal_id = dp.id
where dp.id = $proposal_id
  and (
    coalesce(dp.source_ai,'')='decider_threshold_advisor_v1'
    or coalesce(dp.title,'') like '[decider-tuning]%'
  )
  and coalesce(dp.guard_status,'')='review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(r.review_status,'')='approved';
")"

if [[ "$eligible" = "0" ]]; then
  echo "promotion_not_applied=$proposal_id"
  exit 1
fi

sqlite3 "$DB" "
insert or replace into decider_tuning_promotions(
  proposal_id, promotion_note, promoted_at, source
) values(
  $proposal_id,
  '$note_escaped',
  datetime('now'),
  'promote_decider_tuning_proposal.sh'
);
"

sqlite3 "$DB" "
update dev_proposals
set
  project_decision='backlog',
  decision_note='human_review_promoted',
  guard_status='promoted_review_only',
  guard_reason='decider_tuning_proposal'
where id=$proposal_id;
"

echo "decider_tuning_promoted=$proposal_id"
