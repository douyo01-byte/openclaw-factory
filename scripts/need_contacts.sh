#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
sqlite3 data/openclaw.db "
insert into chat_jobs(chat_id,item_id,role,query,status,created_at,updated_at)
select
  'local',
  $id,
  'scout',
  i.url,
  'new',
  datetime('now'),
  datetime('now')
from items i
where i.id=$id;
"
sqlite3 data/openclaw.db "
select id,chat_id,item_id,role,query,status,created_at
from chat_jobs
where item_id=$id
order by id desc
limit 5;
"
