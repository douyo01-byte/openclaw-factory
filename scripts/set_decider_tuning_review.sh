#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"

proposal_id="${1:-}"
review_status="${2:-}"
review_note="${3:-}"

if [[ -z "$proposal_id" || -z "$review_status" ]]; then
  echo "usage: scripts/set_decider_tuning_review.sh <proposal_id> <approved|rejected|keep_review> [note]" >&2
  exit 1
fi

case "$review_status" in
  approved|rejected|keep_review) ;;
  *)
    echo "invalid review_status: $review_status" >&2
    exit 1
    ;;
esac

sqlite3 "$DB" <<SQL
create table if not exists decider_tuning_reviews(
  proposal_id integer primary key,
  review_status text not null,
  review_note text not null default '',
  reviewed_at text not null default (datetime('now')),
  source text not null default 'review_only_tuning_decider_v1'
);

insert into decider_tuning_reviews(
  proposal_id, review_status, review_note, reviewed_at, source
) values(
  $proposal_id,
  '$review_status',
  '$(printf "%s" "$review_note" | sed "s/'/''/g")',
  datetime('now'),
  'set_decider_tuning_review.sh'
)
on conflict(proposal_id) do update set
  review_status=excluded.review_status,
  review_note=excluded.review_note,
  reviewed_at=datetime('now'),
  source='set_decider_tuning_review.sh';

update dev_proposals
set
  project_decision = case
    when '$review_status'='rejected' then 'archive'
    else coalesce(project_decision,'backlog')
  end,
  decision_note = case
    when '$review_status'='approved' then 'human_review_approved'
    when '$review_status'='rejected' then 'human_review_rejected'
    when '$review_status'='keep_review' then 'human_review_keep_review'
    else coalesce(decision_note,'')
  end
where id=$proposal_id
  and (
    coalesce(source_ai,'')='decider_threshold_advisor_v1'
    or coalesce(title,'') like '[decider-tuning]%'
  )
  and coalesce(guard_status,'')='review_only'
  and coalesce(guard_reason,'')='decider_tuning_proposal';
SQL

echo "decider_tuning_review_set=$proposal_id:$review_status"
