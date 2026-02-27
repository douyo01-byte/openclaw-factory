#!/usr/bin/env bash
set -euo pipefail
DB="${DB:-data/openclaw.db}"
sqlite3 "$DB" <<'SQL'
insert into opportunity(item_id,stage,score_total,risk_total,gate,updated_at)
select i.id,'scan',0,0,'none',datetime('now')
from items i
where not exists (select 1 from opportunity o where o.item_id=i.id);
SQL
