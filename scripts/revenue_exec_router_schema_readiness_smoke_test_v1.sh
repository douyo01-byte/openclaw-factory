#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/revenue_exec_router_schema.XXXXXX")"
DB_PATH="$WORKDIR/revenue_exec_router_schema.sqlite3"
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
  printf '[revenue_exec_router_schema_smoke] %s\n' "$*"
}

log "checking files"
test -f "$ROOT/migrations/20260514_revenue_exec_router_schema_readiness_v1.sql"
test -f "$ROOT/bots/revenue_exec_router_v1.py"

log "checking syntax"
"$PYTHON" -m py_compile "$ROOT/bots/revenue_exec_router_v1.py"
bash -n "$ROOT/scripts/revenue_exec_router_schema_readiness_smoke_test_v1.sh"

log "creating legacy revenue schema without readiness columns"
"$PYTHON" - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.executescript("""
create table revenue_variant_groups (
  id integer primary key autoincrement,
  opportunity_id integer,
  experiment_id integer,
  name text not null default '',
  strategy text not null default 'epsilon_greedy',
  status text not null default 'active',
  winner_experiment_id integer,
  digest_summary text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table revenue_variant_metrics (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  artifact_path text not null default '',
  views integer not null default 0,
  clicks integer not null default 0,
  actions integer not null default 0,
  conversions integer not null default 0,
  score real not null default 0,
  rank integer not null default 0,
  status text not null default 'active',
  source text not null default '',
  captured_at text not null default (datetime('now')),
  unique(group_id, experiment_id)
);

create table revenue_distribution_tasks (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  distribution_type text not null,
  traffic_source text not null default '',
  cta_url text not null default '',
  content text not null default '',
  status text not null default 'planned',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  unique(group_id, experiment_id, distribution_type)
);

create table revenue_memory_patterns (
  id integer primary key autoincrement,
  memory_type text not null,
  pattern text not null,
  horizon_type text not null default 'mid_term',
  economic_summary text not null default '',
  portfolio_summary text not null default '',
  domain_summary text not null default '',
  evidence text not null default '',
  score real not null default 1,
  reuse_count integer not null default 0,
  last_used_at text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  unique(memory_type, pattern)
);
""")
db.commit()
db.close()
PY

log "checking pre-migration fail-fast"
"$PYTHON" - <<'PY'
import sqlite3
from bots import revenue_exec_router_v1

db = sqlite3.connect(revenue_exec_router_v1.DB_PATH)
db.row_factory = sqlite3.Row
try:
    try:
        revenue_exec_router_v1.ensure_schema(db)
    except RuntimeError as exc:
        message = str(exc)
        assert "schema_missing" in message, message
        assert "revenue_variant_metrics" in message, message
        assert "telegram_clicks" in message, message
        assert "ctr" in message, message
        assert "cvr" in message, message
    else:
        raise SystemExit("expected schema_missing before migration")
finally:
    db.close()
PY

log "applying minimal readiness migration to temp db"
sqlite3 "$DB_PATH" < "$ROOT/migrations/20260514_revenue_exec_router_schema_readiness_v1.sql"

log "checking required schema passes"
"$PYTHON" - <<'PY'
import sqlite3
from bots import revenue_exec_router_v1

db = sqlite3.connect(revenue_exec_router_v1.DB_PATH)
db.row_factory = sqlite3.Row
try:
    revenue_exec_router_v1.ensure_schema(db)
    metric_cols = {
        row["name"]
        for row in db.execute("pragma table_info(revenue_variant_metrics)").fetchall()
    }
    dist_cols = {
        row["name"]
        for row in db.execute("pragma table_info(revenue_distribution_tasks)").fetchall()
    }
    assert {"telegram_clicks", "ctr", "cvr"} <= metric_cols, metric_cols
    assert "artifact_path" in dist_cols, dist_cols
finally:
    db.close()
PY

log "complete"
