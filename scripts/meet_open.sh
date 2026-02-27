#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
sqlite3 data/openclaw.db "
insert into opportunity_meeting(item_id,meeting_key,agenda,status,created_at)
values(
  $id,
  strftime('%Y-%m-%d', 'now'),
  'DECIDE: contacts price cogs ship fee ads unit/mo tech/law supply jp_channel owner go/no',
  'new',
  datetime('now')
)
on conflict(item_id,meeting_key) do nothing;
update opportunity set gate='meet', updated_at=datetime('now') where item_id=$id;
"
sqlite3 data/openclaw.db "select item_id,gate,updated_at from opportunity where item_id=$id;"
sqlite3 data/openclaw.db "select id,meeting_key,status,created_at,decided_at from opportunity_meeting where item_id=$id order by id desc limit 3;"
