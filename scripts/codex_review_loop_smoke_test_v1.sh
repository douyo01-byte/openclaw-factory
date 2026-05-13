#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/codex_review_loop.sqlite3"
export DB_PATH
export CODEX_REVIEW_LOOP_MAX_RUNS=5

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

log() {
  printf '[codex_review_loop_smoke] %s\n' "$*"
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
require_file "migrations/20260513_codex_review_loop_v1.sql"
require_file "bots/codex_review_loop_v1.py"
require_file "scripts/codex_review_loop_smoke_test_v1.sh"

log "checking static guards"
require_pattern "codex_run_transcripts" "migrations/20260513_codex_review_loop_v1.sql"
require_pattern "codex_review_queue" "migrations/20260513_codex_review_loop_v1.sql"
require_pattern "Do not commit or push" "bots/codex_review_loop_v1.py"
require_pattern "docs/OPENCLAW_BRAIN.md" "bots/codex_review_loop_v1.py"

if rg -n "git (commit|push)|gh pr|launchctl|openai|chat/completions" "$ROOT/bots/codex_review_loop_v1.py"; then
  log "codex review loop must not automate external execution or LLM calls"
  exit 1
fi

log "checking syntax"
python3 -m py_compile "$ROOT/bots/codex_review_loop_v1.py"
bash -n "$ROOT/scripts/codex_review_loop_smoke_test_v1.sh"

log "creating fake reviewed codex run"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.executescript("""
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

create table codex_task_runs (
  id integer primary key autoincrement,
  task_id integer not null,
  status text not null default 'running',
  dry_run integer not null default 1,
  prompt_text text not null default '',
  result_summary text not null default '',
  error_text text not null default '',
  started_at text not null default (datetime('now')),
  finished_at text not null default '',
  elapsed_seconds real not null default 0
);

insert into codex_tasks
(title, task_text, status, priority, dry_run, timeout_seconds, prompt_text, result_summary)
values
('runtime fix review', 'Review a runtime fix, run py_compile and smoke, do not commit or push.', 'review', 7, 1, 600, 'original prompt', 'ready for review');

insert into codex_task_runs
(task_id, status, dry_run, prompt_text, result_summary, error_text, finished_at, elapsed_seconds)
values
(1, 'review', 1, 'prompt transcript', 'py_compile OK; smoke test OK; residual risk: none', '', datetime('now'), 3);

insert into codex_task_runs
(task_id, status, dry_run, prompt_text, result_summary, error_text, finished_at, elapsed_seconds)
values
(1, 'blocked', 1, 'blocked transcript', '', 'blocked: missing runtime log', datetime('now'), 2);
""")
db.commit()
db.close()
PY

log "running codex review loop"
python3 "$ROOT/bots/codex_review_loop_v1.py"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
queued = db.execute("select * from codex_review_queue order by id").fetchall()
transcripts = db.execute("select * from codex_run_transcripts order by id").fetchall()

assert len(queued) == 2, len(queued)
assert len(transcripts) == 2, len(transcripts)
assert queued[0]["review_status"] == "queued", queued[0]["review_status"]
assert "[CODEX_REVIEW_SUMMARY]" in queued[0]["review_summary"], queued[0]["review_summary"]
assert "[CODEX_REVIEW_FOLLOWUP]" in queued[0]["next_prompt"], queued[0]["next_prompt"]
assert "docs/OPENCLAW_BRAIN.md" in queued[0]["next_prompt"], queued[0]["next_prompt"]
assert "Do not commit or push" in queued[0]["next_prompt"], queued[0]["next_prompt"]
assert "py_compile" in queued[0]["review_summary"], queued[0]["review_summary"]
assert queued[1]["candidate_score"] > queued[0]["candidate_score"], (queued[0]["candidate_score"], queued[1]["candidate_score"])

print("[codex_review_loop_smoke] queued review prompts ok")
db.close()
PY

log "running idempotency check"
python3 "$ROOT/bots/codex_review_loop_v1.py"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
count = db.execute("select count(*) from codex_review_queue").fetchone()[0]
assert count == 2, count
db.close()
print("[codex_review_loop_smoke] idempotency ok")
PY

log "complete"
