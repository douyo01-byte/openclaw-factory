#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
sqlite3 data/openclaw.db "
insert into outreach_log(item_id,item_url,email,channel,status,sent_at,reply_received)
select
  $id,
  i.url,
  c.email,
  'email',
  'todo',
  datetime('now'),
  0
from items i
join contacts c on c.item_url=i.url
where i.id=$id;
"
sqlite3 data/openclaw.db "
select
  item_id,
  channel,
  email,
  status,
  sent_at
from outreach_log
where item_id=$id
order by id desc
limit 50;
"
