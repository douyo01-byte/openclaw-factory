#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
reason="${2:-}"
sqlite3 data/openclaw.db "
insert into opportunity_plan(item_id,notes,updated_at)
values($id,'NO:'||replace('$reason','''',''''''),datetime('now'))
on conflict(item_id) do update set
  notes=case
    when opportunity_plan.notes is null or opportunity_plan.notes='' then excluded.notes
    else opportunity_plan.notes||' '||excluded.notes
  end,
  updated_at=datetime('now');
update opportunity set gate='no', updated_at=datetime('now') where item_id=$id;
update opportunity_meeting set status='decided', decided_at=datetime('now') where item_id=$id and status='new';
"
