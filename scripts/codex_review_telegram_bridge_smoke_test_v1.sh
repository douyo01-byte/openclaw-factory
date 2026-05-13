#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/codex_review_telegram_bridge.sqlite3"
export DB_PATH
export CODEX_REVIEW_TG_THRESHOLD=10
export CODEX_REVIEW_TG_LIMIT=5
export CODEX_REVIEW_TG_DRY_RUN=1

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

log() {
  printf '[codex_review_telegram_bridge_smoke] %s\n' "$*"
}

require_file() {
  local path="$1"
  if [[ ! -f "$ROOT/$path" ]]; then
    log "missing file: $path"
    exit 1
  fi
}

require_pattern() {
  local pattern="$1"
  local path="$2"
  if ! rg -q "$pattern" "$ROOT/$path"; then
    log "missing pattern '$pattern' in $path"
    exit 1
  fi
}

log "checking files"
require_file "migrations/20260513_codex_review_telegram_bridge_v1.sql"
require_file "bots/codex_review_telegram_bridge_v1.py"
require_file "scripts/codex_review_telegram_bridge_smoke_test_v1.sh"

log "checking static guards"
require_pattern "codex_review_telegram_notifications" "migrations/20260513_codex_review_telegram_bridge_v1.sql"
require_pattern "unique\\(queue_id\\)" "migrations/20260513_codex_review_telegram_bridge_v1.sql"
require_pattern "CODEX_REVIEW_TG_DRY_RUN" "bots/codex_review_telegram_bridge_v1.py"
require_pattern "oclibs.telegram" "bots/codex_review_telegram_bridge_v1.py"

if rg -n "launchctl|git (commit|push)|chat/completions|openai" "$ROOT/bots/codex_review_telegram_bridge_v1.py"; then
  log "bridge must not automate launchctl, git, or LLM calls"
  exit 1
fi

log "checking syntax"
python3 -m py_compile "$ROOT/bots/codex_review_telegram_bridge_v1.py"
bash -n "$ROOT/scripts/codex_review_telegram_bridge_smoke_test_v1.sh"

log "creating fake review queue"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.executescript("""
create table codex_review_queue (
  id integer primary key autoincrement,
  source_task_id integer not null default 0,
  source_run_id integer not null default 0,
  review_status text not null default 'queued',
  candidate_score real not null default 0,
  review_summary text not null default '',
  next_prompt text not null default '',
  approval_note text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  unique(source_run_id)
);

insert into codex_review_queue
(source_task_id, source_run_id, review_status, candidate_score, review_summary, next_prompt)
values
(101, 201, 'queued', 15, '[CODEX_REVIEW_SUMMARY]\nrisk: no explicit residual risk found\nresult: py_compile OK', 'next prompt'),
(102, 202, 'queued', 5, '[CODEX_REVIEW_SUMMARY]\nrisk: below threshold', 'next prompt'),
(103, 203, 'done', 50, '[CODEX_REVIEW_SUMMARY]\nrisk: already done', 'next prompt');
""")
db.commit()
db.close()
PY

log "running dry-run bridge"
python3 "$ROOT/bots/codex_review_telegram_bridge_v1.py" > "$WORKDIR/dry_run.out"
cat "$WORKDIR/dry_run.out"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
notified = db.execute("select count(*) from codex_review_telegram_notifications").fetchone()[0]
assert notified == 0, notified
db.close()
PY

if ! rg -q "queue_id: 1" "$WORKDIR/dry_run.out"; then
  log "expected high score queued item in dry-run output"
  exit 1
fi
if rg -q "queue_id: 2|queue_id: 3" "$WORKDIR/dry_run.out"; then
  log "unexpected low-score or non-queued item in dry-run output"
  exit 1
fi

log "checking duplicate guard"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.execute("""
insert into codex_review_telegram_notifications
(queue_id, source_task_id, source_run_id, candidate_score, message_id)
values (1, 101, 201, 15, 'fake-message')
""")
try:
    db.execute("""
    insert into codex_review_telegram_notifications
    (queue_id, source_task_id, source_run_id, candidate_score, message_id)
    values (1, 101, 201, 15, 'duplicate')
    """)
except sqlite3.IntegrityError:
    pass
else:
    raise AssertionError("duplicate queue_id insert should fail")
db.commit()
db.close()
PY

log "running idempotency after notification marker"
python3 "$ROOT/bots/codex_review_telegram_bridge_v1.py" > "$WORKDIR/idempotent.out"
cat "$WORKDIR/idempotent.out"
if ! rg -q "candidates=0 sent=0" "$WORKDIR/idempotent.out"; then
  log "expected no candidates after notification marker"
  exit 1
fi

log "complete"
