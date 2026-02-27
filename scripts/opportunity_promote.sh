#!/usr/bin/env bash
set -euo pipefail
id="${1:?item_id}"

sqlite3 data/openclaw.db <<SQL
INSERT INTO opportunity(item_id,stage,gate,updated_at)
VALUES($id,'review','meet',datetime('now'))
ON CONFLICT(item_id) DO UPDATE SET
  stage='review',
  gate='meet',
  updated_at=datetime('now');
SQL
