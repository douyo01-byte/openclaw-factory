#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/router_core_schema.sqlite3"
export DB_PATH
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

log() {
  printf '[router_core_schema_smoke] %s\n' "$*"
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
require_file "migrations/20260513_router_core_schema_v1.sql"
require_file "bots/telegram_ops_executor_v1.py"
require_file "bots/kaikun04_router_worker_v1.py"
require_file "bots/kaikun04_exec_bridge_v1.py"
require_file "bots/task_router_v1.py"
require_file "scripts/router_core_schema_smoke_test_v1.sh"

log "checking static guards"
require_pattern "router_tasks add column reply_text" "migrations/20260513_router_core_schema_v1.sql"
require_pattern "self_improvement_log add column status" "migrations/20260513_router_core_schema_v1.sql"
require_pattern "inbox_commands add column router_status" "migrations/20260513_router_core_schema_v1.sql"
for path in bots/telegram_ops_executor_v1.py bots/kaikun04_router_worker_v1.py bots/kaikun04_exec_bridge_v1.py bots/task_router_v1.py; do
  require_pattern "schema_missing" "$path"
  if rg -n "alter table|create table if not exists" "$ROOT/$path"; then
    log "runtime schema mutation remains in $path"
    exit 1
  fi
done

log "checking syntax"
"$PYTHON" -m py_compile \
  "$ROOT/bots/telegram_ops_executor_v1.py" \
  "$ROOT/bots/kaikun04_router_worker_v1.py" \
  "$ROOT/bots/kaikun04_exec_bridge_v1.py" \
  "$ROOT/bots/task_router_v1.py"
bash -n "$ROOT/scripts/router_core_schema_smoke_test_v1.sh"

log "creating pre-migration base schema"
"$PYTHON" - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.executescript("""
create table inbox_commands (
  id integer primary key autoincrement,
  chat_id text not null default '',
  message_id integer,
  reply_to_message_id integer,
  from_username text,
  from_name text,
  text text not null default '',
  received_at text default (datetime('now')),
  applied_at text,
  status text default 'new',
  error text
);

create table router_tasks (
  id integer primary key autoincrement,
  source_command_id integer,
  mode text not null default 'FAST',
  target_bot text not null default 'kaikun04',
  task_text text not null,
  status text not null default 'new',
  created_at text default (datetime('now')),
  updated_at text default (datetime('now'))
);

create table self_improvement_log (
  id integer primary key autoincrement,
  parent_task_id integer not null,
  child_task_id integer,
  source_command_id integer,
  kind text not null default 'exec_bridge',
  problem text not null default '',
  fix text not null default '',
  result text not null default '',
  reusable_pattern text not null default '',
  created_at text default (datetime('now'))
);
""")
db.commit()
db.close()
PY

log "checking pre-migration fail-fast"
"$PYTHON" - <<'PY'
import os
import sqlite3
from bots import telegram_ops_executor_v1

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
try:
    telegram_ops_executor_v1.ensure_schema(db)
except RuntimeError as exc:
    assert "schema_missing" in str(exc), exc
else:
    raise AssertionError("expected schema_missing before migration")
finally:
    db.close()
PY

log "applying router core migration through runner"
"$PYTHON" "$ROOT/bots/migration_runner_v1.py" apply "$ROOT/migrations/20260513_router_core_schema_v1.sql"

log "checking required columns"
"$PYTHON" - <<'PY'
import os
import sqlite3
from bots import telegram_ops_executor_v1, kaikun04_router_worker_v1, kaikun04_exec_bridge_v1, task_router_v1

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
checks = {
    "router_tasks": {
        "parent_task_id", "task_role", "clean_prompt", "reply_text", "result_text",
        "sent_message_id", "started_at", "finished_at", "validation_status",
        "validation_reason", "retry_count", "exec_bridge_status",
        "exec_bridge_reason", "exec_child_task_id",
    },
    "inbox_commands": {
        "source", "processed", "router_status", "router_target", "router_mode", "router_finish_status",
        "router_task_id", "updated_at",
    },
    "self_improvement_log": {
        "status", "parent_reply_head", "child_result_head", "applied_at", "updated_at",
    },
}
for table, required in checks.items():
    cols = {r["name"] for r in db.execute(f"pragma table_info({table})")}
    missing = required - cols
    assert not missing, (table, sorted(missing))

telegram_ops_executor_v1.ensure_schema(db)
kaikun04_router_worker_v1.ensure_schema(db)
kaikun04_exec_bridge_v1.ensure_schema(db)
task_router_v1.ensure_schema(db)
status = db.execute("select status from openclaw_migration_ledger where migration_name='20260513_router_core_schema_v1.sql'").fetchone()[0]
assert status == "applied", status
db.close()
PY

log "checking runner skip"
"$PYTHON" "$ROOT/bots/migration_runner_v1.py" apply "$ROOT/migrations/20260513_router_core_schema_v1.sql" > "$WORKDIR/skip.out"
cat "$WORKDIR/skip.out"
rg -q "skip applied 20260513_router_core_schema_v1.sql" "$WORKDIR/skip.out"

log "complete"
