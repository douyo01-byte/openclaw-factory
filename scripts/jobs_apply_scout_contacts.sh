#!/usr/bin/env bash
set -euo pipefail
DB="${DB:-data/openclaw.db}"
id="${1:?item_id}"
url="$(sqlite3 "$DB" "select url from items where id=$id;")"
[ -n "$url" ] || exit 1
u="${url//\'/\'\'}"
sqlite3 "$DB" <<SQL
delete from chat_jobs where role='scout' and status='new' and item_id=$id;
insert into chat_jobs(chat_id,item_id,role,query,status,created_at,updated_at,prompt)
values('', $id, 'scout', '$u', 'new', datetime('now'), datetime('now'), '$u');
SQL
python -m bots.command_apply_v1 >/dev/null 2>&1 || true
