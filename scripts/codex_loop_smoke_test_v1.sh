#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/codex_loop_smoke.sqlite3"
export DB_PATH
export CODEX_LOOP_DRY_RUN=1
export CODEX_LOOP_MAX_TASKS=1

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

log() {
  printf '[codex_loop_smoke] %s\n' "$*"
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
require_file "bots/codex_task_bridge_v1.py"
require_file "scripts/generated/run_codex_loop.sh"
require_file "migrations/20260513_codex_autonomous_loop_v1.sql"
require_file "docs/OPENCLAW_BRAIN.md"

log "checking static guards"
require_pattern "codex_tasks" "bots/codex_task_bridge_v1.py"
require_pattern "codex_task_runs" "bots/codex_task_bridge_v1.py"
require_pattern "Do not commit or push" "bots/codex_task_bridge_v1.py"
require_pattern "docs/OPENCLAW_BRAIN.md" "bots/codex_task_bridge_v1.py"
require_pattern "smoke test" "bots/codex_task_bridge_v1.py"
require_pattern "CODEX_LOOP_DRY_RUN" "scripts/generated/run_codex_loop.sh"

if rg -n "git (commit|push)|gh pr|launchctl" "$ROOT/bots/codex_task_bridge_v1.py" "$ROOT/scripts/generated/run_codex_loop.sh"; then
  log "codex loop must not automate commit/push/launchctl"
  exit 1
fi

log "compiling bridge"
python3 -m py_compile "$ROOT/bots/codex_task_bridge_v1.py"

log "creating fake codex task"
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
(title, task_text, status, priority, dry_run, timeout_seconds)
values
('fake codex task', 'Inspect one file, run smoke, save result. Do not commit or push.', 'new', 10, 1, 60);

insert into codex_tasks
(title, task_text, status, priority, dry_run, timeout_seconds, updated_at)
values
('timeout task', 'This running task should become blocked.', 'running', 0, 1, 1, datetime('now', '-10 minutes'));

insert into codex_task_runs
(task_id, status, dry_run, started_at)
values
(2, 'running', 1, datetime('now', '-10 minutes'));
""")
db.commit()
db.close()
PY

log "running bridge dry-run"
python3 "$ROOT/bots/codex_task_bridge_v1.py"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
task = db.execute("select * from codex_tasks where id=1").fetchone()
run = db.execute("select * from codex_task_runs where task_id=1").fetchone()
blocked = db.execute("select * from codex_tasks where id=2").fetchone()
blocked_run = db.execute("select * from codex_task_runs where task_id=2").fetchone()

assert task["status"] == "review", task["status"]
assert "DRY_RUN" in task["result_summary"], task["result_summary"]
assert "no commit or push" in task["result_summary"], task["result_summary"]
assert "docs/OPENCLAW_BRAIN.md" in task["prompt_text"], task["prompt_text"]
assert "minimal" in task["prompt_text"].lower(), task["prompt_text"]
assert "smoke" in task["prompt_text"].lower(), task["prompt_text"]
assert run and run["status"] == "review", run["status"] if run else "missing run"
assert "DRY_RUN" in run["result_summary"], run["result_summary"]
assert blocked["status"] == "blocked", blocked["status"]
assert "timeout" in blocked["result_summary"], blocked["result_summary"]
assert blocked_run["status"] == "blocked", blocked_run["status"]
db.close()
print("[codex_loop_smoke] fake result save ok")
PY

log "dry-run complete; no commit/push/launchctl was executed"
