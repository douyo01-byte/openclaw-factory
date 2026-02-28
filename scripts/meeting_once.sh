#!/usr/bin/env bash
set -euo pipefail
DB="${DB:-data/openclaw.db}"
sqlite3 "$DB" -csv "
select o.item_id
from opportunity o
join opportunity_plan p on p.item_id=o.item_id
where o.gate='meet'
and coalesce(p.digest_sent_at,'')=''
" | awk -F, 'NF&&$1!=""{print $1}' | while read -r id; do
  python -m bots.meeting_from_db_v1 --item "$id" >/dev/null 2>&1 || true
  sqlite3 "$DB" "update opportunity_plan set digest_sent_at=datetime('now') where item_id=$id;"
done
