#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/codex_review_approval.sqlite3"
export DB_PATH

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

log() {
  printf '[codex_review_approval_smoke] %s\n' "$*"
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
require_file "migrations/20260513_codex_review_approval_v1.sql"
require_file "bots/codex_review_approval_v1.py"
require_file "scripts/set_codex_review_status_v1.sh"
require_file "scripts/codex_review_approval_smoke_test_v1.sh"

log "checking static guards"
require_pattern "created_codex_task_id" "migrations/20260513_codex_review_approval_v1.sql"
require_pattern "begin immediate" "bots/codex_review_approval_v1.py"
require_pattern "created_codex_task_id=0" "bots/codex_review_approval_v1.py"
require_pattern "'new'" "bots/codex_review_approval_v1.py"

if rg -n "launchctl|git (commit|push)|gh pr|chat/completions|openai|subprocess" "$ROOT/bots/codex_review_approval_v1.py"; then
  log "approval CLI must not launch services, execute git, call LLMs, or run subprocesses"
  exit 1
fi

log "checking syntax"
python3 -m py_compile "$ROOT/bots/codex_review_approval_v1.py"
bash -n "$ROOT/scripts/set_codex_review_status_v1.sh"
bash -n "$ROOT/scripts/codex_review_approval_smoke_test_v1.sh"

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

create table codex_tasks (
  id integer primary key autoincrement,
  title text not null default '',
  task_text text not null,
  status text not null default 'new',
  priority integer not null default 0,
  dry_run integer not null default 1,
  timeout_seconds integer not null default 1800,
  prompt_text text not null default '',
  result_summary text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

insert into codex_review_queue
(source_task_id, source_run_id, review_status, candidate_score, review_summary, next_prompt)
values
(101, 201, 'queued', 15, '[CODEX_REVIEW_SUMMARY]\\nrisk: none', '[CODEX_REVIEW_FOLLOWUP]\\nverify and report only'),
(102, 202, 'queued', 8, '[CODEX_REVIEW_SUMMARY]\\nrisk: reject', '[CODEX_REVIEW_FOLLOWUP]\\nblocked'),
(103, 203, 'queued', 20, '[CODEX_REVIEW_SUMMARY]\\nrisk: empty prompt', '');
""")
db.commit()
db.close()
PY

log "applying approval migration"
sqlite3 "$DB_PATH" < "$ROOT/migrations/20260513_codex_review_approval_v1.sql"

log "approving queue 1"
python3 "$ROOT/bots/codex_review_approval_v1.py" approve 1 "human approved"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
q = db.execute("select * from codex_review_queue where id=1").fetchone()
t = db.execute("select * from codex_tasks where id=?", (q["created_codex_task_id"],)).fetchone()
assert q["review_status"] == "approved", q["review_status"]
assert q["created_codex_task_id"] > 0, q["created_codex_task_id"]
assert "human approved" in q["approval_note"], q["approval_note"]
assert t["status"] == "new", t["status"]
assert t["dry_run"] == 1, t["dry_run"]
assert "[CODEX_REVIEW_FOLLOWUP]" in t["task_text"], t["task_text"]
assert "created from codex_review_queue id=1" in t["result_summary"], t["result_summary"]
db.close()
PY

log "checking duplicate approve guard"
if python3 "$ROOT/bots/codex_review_approval_v1.py" approve 1 "duplicate" > "$WORKDIR/dup.out" 2>&1; then
  cat "$WORKDIR/dup.out"
  log "duplicate approve should fail"
  exit 1
fi
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
count = db.execute("select count(*) from codex_tasks").fetchone()[0]
assert count == 1, count
db.close()
PY

log "rejecting queue 2"
python3 "$ROOT/bots/codex_review_approval_v1.py" reject 2 "not needed"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
q = db.execute("select * from codex_review_queue where id=2").fetchone()
assert q["review_status"] == "rejected", q["review_status"]
assert q["created_codex_task_id"] == 0, q["created_codex_task_id"]
assert "not needed" in q["approval_note"], q["approval_note"]
count = db.execute("select count(*) from codex_tasks").fetchone()[0]
assert count == 1, count
db.close()
PY

log "checking empty prompt guard"
if python3 "$ROOT/bots/codex_review_approval_v1.py" approve 3 "empty" > "$WORKDIR/empty.out" 2>&1; then
  cat "$WORKDIR/empty.out"
  log "empty prompt approve should fail"
  exit 1
fi

log "checking wrapper"
DB_PATH="$DB_PATH" bash "$ROOT/scripts/set_codex_review_status_v1.sh" reject 3 "wrapper reject"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
status = db.execute("select review_status from codex_review_queue where id=3").fetchone()[0]
assert status == "rejected", status
db.close()
PY

log "complete"
