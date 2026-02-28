#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
sqlite3 data/openclaw.db "
update opportunity set stage='exec', gate='done', updated_at=datetime('now') where item_id=$id;
"
sqlite3 data/openclaw.db "select item_id,stage,gate,updated_at from opportunity where item_id=$id;"
