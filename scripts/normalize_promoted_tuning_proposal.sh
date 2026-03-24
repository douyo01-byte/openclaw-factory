#!/bin/zsh
set -euo pipefail
cd ~/AI/openclaw-factory-daemon || exit 1
DB="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
proposal_id="${1:-}"
note="${2:-normalized by normalize_promoted_tuning_proposal.sh}"
if [[ -z "$proposal_id" ]]; then
  echo "usage: scripts/normalize_promoted_tuning_proposal.sh <proposal_id> [note]" >&2
  exit 1
fi
note_escaped="$(printf "%s" "$note" | sed "s/'/''/g")"
sqlite3 "$DB" "
create table if not exists decider_tuning_normalizations(
  proposal_id integer primary key,
  normalize_note text not null default '',
  normalized_at text not null default (datetime('now')),
  source text not null default 'normalize_promoted_tuning_proposal.sh'
);
insert into decider_tuning_normalizations(
  proposal_id, normalize_note, normalized_at, source
)
select
  dp.id,
  '$note_escaped',
  datetime('now'),
  'normalize_promoted_tuning_proposal.sh'
from dev_proposals dp
join decider_tuning_normalization_plan p on p.proposal_id = dp.id
where dp.id=$proposal_id
  and coalesce(dp.guard_status,'')='released_review_only'
  and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
  and coalesce(p.normalize_action,'')='ready_for_normalization'
on conflict(proposal_id) do update set
  normalize_note=excluded.normalize_note,
  normalized_at=datetime('now'),
  source='normalize_promoted_tuning_proposal.sh';
update dev_proposals
set
  project_decision='backlog',
  decision_note='human_review_normalized',
  guard_status='normalized_review_only',
  guard_reason='decider_tuning_proposal'
where id in (
  select dp.id
  from dev_proposals dp
  join decider_tuning_normalization_plan p on p.proposal_id = dp.id
  where dp.id=$proposal_id
    and coalesce(dp.guard_status,'')='released_review_only'
    and coalesce(dp.guard_reason,'')='decider_tuning_proposal'
    and coalesce(p.normalize_action,'')='ready_for_normalization'
);
"
changed="$(sqlite3 "$DB" "select changes();")"
if [[ "$changed" = "0" ]]; then
  echo "decider_tuning_normalization_not_applied=$proposal_id"
  exit 1
fi
echo "decider_tuning_normalized=$proposal_id"
