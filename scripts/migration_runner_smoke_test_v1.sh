#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/migration_runner.sqlite3"
export DB_PATH

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

log() {
  printf '[migration_runner_smoke] %s\n' "$*"
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
require_file "migrations/20260513_migration_ledger_v1.sql"
require_file "bots/migration_runner_v1.py"
require_file "scripts/migration_runner_smoke_test_v1.sh"

log "checking static guards"
require_pattern "openclaw_migration_ledger" "migrations/20260513_migration_ledger_v1.sql"
require_pattern "sha256" "bots/migration_runner_v1.py"
require_pattern "hash mismatch" "bots/migration_runner_v1.py"
require_pattern "failed ledger status" "bots/migration_runner_v1.py"
require_pattern "mark-applied" "bots/migration_runner_v1.py"

if rg -n "launchctl|git (commit|push)|gh pr|chat/completions|openai|requests|urllib" "$ROOT/bots/migration_runner_v1.py"; then
  log "migration runner must not launch services, use git, call LLMs, or use network"
  exit 1
fi

log "checking syntax"
python3 -m py_compile "$ROOT/bots/migration_runner_v1.py"
bash -n "$ROOT/scripts/migration_runner_smoke_test_v1.sh"

GOOD_SQL="$WORKDIR/001_create_widget.sql"
MARK_SQL="$WORKDIR/002_mark_only.sql"
BAD_SQL="$WORKDIR/003_bad.sql"

cat > "$GOOD_SQL" <<'SQL'
create table widgets (
  id integer primary key autoincrement,
  name text not null default ''
);
SQL

cat > "$MARK_SQL" <<'SQL'
create table mark_only (
  id integer primary key autoincrement
);
SQL

cat > "$BAD_SQL" <<'SQL'
create table broken_table (
  id integer primary key,
SQL

log "initial status"
python3 "$ROOT/bots/migration_runner_v1.py" status > "$WORKDIR/status_empty.out"
cat "$WORKDIR/status_empty.out"
rg -q "no migrations recorded" "$WORKDIR/status_empty.out"

log "applying good migration"
python3 "$ROOT/bots/migration_runner_v1.py" apply "$GOOD_SQL" > "$WORKDIR/apply_good.out"
cat "$WORKDIR/apply_good.out"
rg -q "applied 001_create_widget.sql" "$WORKDIR/apply_good.out"

log "checking applied side effects"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
assert "widgets" in tables, tables
row = db.execute("select migration_name, status, length(sha256) from openclaw_migration_ledger where migration_name='001_create_widget.sql'").fetchone()
assert row == ("001_create_widget.sql", "applied", 64), row
db.close()
PY

log "checking applied skip"
python3 "$ROOT/bots/migration_runner_v1.py" apply "$GOOD_SQL" > "$WORKDIR/apply_skip.out"
cat "$WORKDIR/apply_skip.out"
rg -q "skip applied 001_create_widget.sql" "$WORKDIR/apply_skip.out"

log "checking hash mismatch fail-fast"
cat >> "$GOOD_SQL" <<'SQL'
create table drift_marker (id integer primary key);
SQL
if python3 "$ROOT/bots/migration_runner_v1.py" apply "$GOOD_SQL" > "$WORKDIR/hash_mismatch.out" 2>&1; then
  cat "$WORKDIR/hash_mismatch.out"
  log "hash mismatch should fail"
  exit 1
fi
cat "$WORKDIR/hash_mismatch.out"
rg -q "hash mismatch" "$WORKDIR/hash_mismatch.out"

log "checking mark-applied"
python3 "$ROOT/bots/migration_runner_v1.py" mark-applied "$MARK_SQL" > "$WORKDIR/mark.out"
cat "$WORKDIR/mark.out"
rg -q "marked applied 002_mark_only.sql" "$WORKDIR/mark.out"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
assert "mark_only" not in tables, tables
status = db.execute("select status from openclaw_migration_ledger where migration_name='002_mark_only.sql'").fetchone()[0]
assert status == "applied", status
db.close()
PY

log "checking failed migration record"
if python3 "$ROOT/bots/migration_runner_v1.py" apply "$BAD_SQL" > "$WORKDIR/bad.out" 2>&1; then
  cat "$WORKDIR/bad.out"
  log "bad migration should fail"
  exit 1
fi
cat "$WORKDIR/bad.out"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
row = db.execute("select status, error_text from openclaw_migration_ledger where migration_name='003_bad.sql'").fetchone()
assert row[0] == "failed", row
assert row[1], row
db.close()
PY

log "checking failed migration fail-fast"
if python3 "$ROOT/bots/migration_runner_v1.py" apply "$BAD_SQL" > "$WORKDIR/bad_retry.out" 2>&1; then
  cat "$WORKDIR/bad_retry.out"
  log "failed migration retry should fail-fast"
  exit 1
fi
cat "$WORKDIR/bad_retry.out"
rg -q "failed ledger status" "$WORKDIR/bad_retry.out"

log "checking status output"
python3 "$ROOT/bots/migration_runner_v1.py" status > "$WORKDIR/status.out"
cat "$WORKDIR/status.out"
rg -q "001_create_widget.sql" "$WORKDIR/status.out"
rg -q "002_mark_only.sql" "$WORKDIR/status.out"
rg -q "003_bad.sql" "$WORKDIR/status.out"

log "complete"
