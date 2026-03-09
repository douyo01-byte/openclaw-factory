#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate

DB=data/openclaw.db

sqlite3 "$DB" "PRAGMA busy_timeout=5000;"

ids=$(sqlite3 "$DB" "
select id,pr_number
from dev_proposals
where dev_stage='pr_created';
")

while IFS="|" read -r id pr; do
  [ -z "$id" ] && continue

  state=$(gh pr view "$pr" \
    --repo douyo01-byte/openclaw-factory \
    --json state \
    --jq '.state' 2>/dev/null || echo "")

  if [ "$state" = "MERGED" ]; then
    sqlite3 "$DB" "
    update dev_proposals
    set status='merged',
        dev_stage='merged',
        pr_status='merged'
    where id=$id;
    update proposal_state
    set stage='merged',
        updated_at=datetime('now')
    where proposal_id=$id;
    "
  fi
done <<< "$ids"
