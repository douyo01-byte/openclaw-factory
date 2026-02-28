#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
sqlite3 data/openclaw.db "
select
  $id as item_id,
  coalesce(i.title,'') as title,
  replace(replace(replace(coalesce(i.url,''),'https://',''),'http://',''),'www.','') as url,
  count(c.email) as contacts_n
from items i
left join contacts c on c.item_url=i.url
where i.id=$id;
"
