#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
sqlite3 data/openclaw.db "
update opportunity set gate='go', updated_at=datetime('now') where item_id=$id;
update opportunity_meeting set status='decided', decided_at=datetime('now') where item_id=$id and status='new';
"
