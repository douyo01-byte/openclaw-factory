#!/bin/bash
set -euo pipefail
msg="${1:-[FAST] telegram ops smoke}"
DB="${DB_PATH:-/Users/doyopc/AI/openclaw-factory/data/openclaw.db}"
sqlite3 "$DB" "
insert into inbox_commands(source, text, status, processed, created_at, updated_at)
values('manual', '$(printf "%s" "$msg" | sed "s/'/''/g")', 'pending', 0, datetime('now'), datetime('now'));
"
sqlite3 "$DB" "
select id, source, status, processed, substr(text,1,120), updated_at
from inbox_commands
order by id desc
limit 3;
"
