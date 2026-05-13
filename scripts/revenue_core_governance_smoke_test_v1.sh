#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/revenue_core_governance.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
DB="$TMP_DIR/revenue_governance.db"
PRE_DB="$TMP_DIR/revenue_governance_pre.db"

echo "[revenue_core_governance_smoke] checking files"
test -f migrations/20260513_revenue_core_schema_v2.sql
test -f bots/revenue_bandit_v1.py
test -f bots/revenue_exec_router_v1.py
test -f bots/revenue_publish_approval_server_v1.py

echo "[revenue_core_governance_smoke] checking static guards"
if rg -n "alter table|create table if not exists" \
  bots/revenue_bandit_v1.py \
  bots/revenue_exec_router_v1.py \
  bots/revenue_publish_approval_server_v1.py >"$TMP_DIR/static.txt"; then
  cat "$TMP_DIR/static.txt"
  echo "runtime schema mutation remains" >&2
  exit 1
fi
for file in \
  bots/revenue_bandit_v1.py \
  bots/revenue_exec_router_v1.py \
  bots/revenue_publish_approval_server_v1.py; do
  rg -n "schema_missing" "$file" >/dev/null
  rg -n "20260513_revenue_core_schema_v2.sql" "$file" >/dev/null
done

echo "[revenue_core_governance_smoke] checking syntax"
"$PYTHON" -m py_compile \
  bots/revenue_bandit_v1.py \
  bots/revenue_exec_router_v1.py \
  bots/revenue_publish_approval_server_v1.py

echo "[revenue_core_governance_smoke] checking pre-migration fail-fast"
DB_PATH="$PRE_DB" "$PYTHON" - <<'PY'
import sqlite3
from bots import revenue_bandit_v1

db = sqlite3.connect(revenue_bandit_v1.DB_PATH)
db.row_factory = sqlite3.Row
db.execute("create table revenue_memory_patterns (id integer primary key autoincrement, memory_type text not null, pattern text not null)")
try:
    revenue_bandit_v1.ensure_schema(db)
except RuntimeError as exc:
    assert "schema_missing" in str(exc), str(exc)
else:
    raise SystemExit("expected schema_missing before migration")
PY

echo "[revenue_core_governance_smoke] applying revenue governance migration through runner"
DB_PATH="$DB" "$PYTHON" - <<'PY'
import sqlite3
import os

db = sqlite3.connect(os.environ["DB_PATH"])
db.executescript("""
create table revenue_opportunities (
  id integer primary key autoincrement,
  source text not null default 'manual',
  title text not null,
  description text not null default '',
  market text not null default '',
  monetization_type text not null default '',
  expected_profit_score integer not null default 0,
  validation_speed_score integer not null default 0,
  cost_score integer not null default 0,
  automation_score integer not null default 0,
  risk_score integer not null default 0,
  total_score integer not null default 0,
  status text not null default 'new',
  rationale text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);
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
db.close()
PY
DB_PATH="$DB" "$PYTHON" bots/migration_runner_v1.py apply migrations/20260513_revenue_core_schema_v2.sql

echo "[revenue_core_governance_smoke] checking required columns"
DB_PATH="$DB" "$PYTHON" - <<'PY'
from bots import revenue_bandit_v1, revenue_exec_router_v1, revenue_publish_approval_server_v1

db = revenue_bandit_v1.con()
try:
    revenue_bandit_v1.ensure_schema(db)
    revenue_exec_router_v1.ensure_schema(db)
    revenue_publish_approval_server_v1.ensure_schema(db)
finally:
    db.close()
PY

echo "[revenue_core_governance_smoke] checking runner skip"
DB_PATH="$DB" "$PYTHON" bots/migration_runner_v1.py apply migrations/20260513_revenue_core_schema_v2.sql | rg "skip applied 20260513_revenue_core_schema_v2.sql" >/dev/null

echo "[revenue_core_governance_smoke] complete"
