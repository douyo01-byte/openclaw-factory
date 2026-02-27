#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"
owner="${2:-}"
jp="${3:-}"
sqlite3 data/openclaw.db <<SQL
INSERT INTO opportunity_plan(item_id,notes,updated_at)
VALUES($id,'owner=$owner jp=$jp',datetime('now'))
ON CONFLICT(item_id) DO UPDATE SET
  notes=case
    when opportunity_plan.notes is null or opportunity_plan.notes=''
      then excluded.notes
      else opportunity_plan.notes||' '||excluded.notes
  end,
  updated_at=datetime('now');
UPDATE opportunity SET gate='go', updated_at=datetime('now') WHERE item_id=$id;
UPDATE opportunity_meeting SET status='decided', decided_at=datetime('now')
WHERE item_id=$id AND status='new';
SQL
