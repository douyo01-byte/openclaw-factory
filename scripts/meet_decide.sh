#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
gate="${2:?go|no|meet}"
reason="${3:-}"
case "$gate" in
  go) scripts/go.sh "$id" ;;
  no) scripts/no.sh "$id" "$reason" ;;
  meet) sqlite3 data/openclaw.db "update opportunity set gate='meet', updated_at=datetime('now') where item_id=$id;" ;;
  *) exit 2 ;;
esac
sqlite3 data/openclaw.db "select item_id,gate,updated_at from opportunity where item_id=$id;"
sqlite3 data/openclaw.db "select id,status,decided_at from opportunity_meeting where item_id=$id order by id desc limit 1;"
