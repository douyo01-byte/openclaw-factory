#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/revenue_exec_router_dry_run.XXXXXX")"
DB_PATH="$WORKDIR/revenue_exec_router_dry_run.sqlite3"
OUT="$WORKDIR/dry_run.out"
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
  printf '[revenue_exec_router_dry_run_smoke] %s\n' "$*"
}

log "checking syntax"
"$PYTHON" -m py_compile "$ROOT/bots/revenue_exec_router_v1.py"
bash -n "$ROOT/scripts/revenue_exec_router_dry_run_smoke_test_v1.sh"

log "creating isolated smoke database"
"$PYTHON" - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.executescript("""
create table router_tasks (
  id integer primary key autoincrement,
  parent_task_id integer,
  target_bot text not null default 'kaikun04',
  mode text not null default 'THINK',
  status text not null default 'new',
  task_text text not null,
  reply_text text not null default '',
  created_at text default (datetime('now')),
  updated_at text default (datetime('now'))
);

create table revenue_experiments (
  id integer primary key autoincrement,
  opportunity_id integer,
  experiment_type text not null,
  title text not null,
  hypothesis text not null,
  validation_method text not null,
  expected_signal text not null,
  expected_cost integer not null default 0,
  expected_validation_hours integer not null default 24,
  status text not null default 'new',
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
  telegram_clicks integer not null default 0,
  actions integer not null default 0,
  conversions integer not null default 0,
  ctr real not null default 0,
  cvr real not null default 0,
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
  artifact_path text not null default '',
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
  updated_at text not null default (datetime('now'))
);

insert into revenue_experiments
(id, opportunity_id, experiment_type, title, hypothesis, validation_method, expected_signal, expected_cost, expected_validation_hours, status)
values
(2, 1, 'observation_only', 'dry-run smoke experiment', 'dry-run keeps database unchanged', 'no-send/no-deploy observation', 'preview only', 0, 24, 'new');

insert into revenue_memory_patterns
(memory_type, pattern, horizon_type, economic_summary, portfolio_summary, domain_summary, score, reuse_count)
values
('copy', 'show one clear CTA', 'mid_term', 'positive ROI hint', 'reuse existing asset', 'lp', 1.0, 0);

insert into router_tasks(target_bot, mode, status, task_text)
values('kaikun04', 'THINK', 'new', '[REVENUE_CORE]
Experiment:
- id: 2
- type: observation_only
- title: dry-run smoke experiment
- hypothesis: dry-run keeps database unchanged
- validation_method: no-send/no-deploy observation
- expected_signal: preview only
');
""")
db.commit()
db.close()
PY

before_counts="$(sqlite3 "$DB_PATH" "select (select count(*) from router_tasks)||','||(select count(*) from revenue_experiments)||','||(select count(*) from revenue_variant_groups)||','||(select count(*) from revenue_variant_metrics)||','||(select count(*) from revenue_distribution_tasks)||','||(select coalesce(sum(reuse_count),0) from revenue_memory_patterns);")"

log "running dry-run preview"
REVENUE_EXEC_ROUTER_DRY_RUN=1 REVENUE_EXPERIMENT_ID=2 "$PYTHON" "$ROOT/bots/revenue_exec_router_v1.py" > "$OUT"

after_counts="$(sqlite3 "$DB_PATH" "select (select count(*) from router_tasks)||','||(select count(*) from revenue_experiments)||','||(select count(*) from revenue_variant_groups)||','||(select count(*) from revenue_variant_metrics)||','||(select count(*) from revenue_distribution_tasks)||','||(select coalesce(sum(reuse_count),0) from revenue_memory_patterns);")"
test "$before_counts" = "$after_counts"

grep -q "DRY_RUN revenue_exec_router_v1" "$OUT"
grep -q "experiment id=2 status=new experiment_type=observation_only title=dry-run smoke experiment" "$OUT"
grep -q "would_create router_task parent_task_id=1 target_bot=ops_exec mode=EXEC status=new variant=A" "$OUT"
grep -q "would_create revenue_variant_metric group_id=new experiment_id=2 variant_key=A status=active source=router_seed" "$OUT"
grep -q "would_create revenue_distribution_task group_id=new experiment_id=2 variant_key=A distribution_type=telegram_post" "$OUT"
grep -q "dry_run complete; no INSERT/UPDATE/commit executed" "$OUT"

log "complete"
