#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/revenue_smoke.sqlite3"
export DB_PATH

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

log() {
  printf '[revenue_smoke] %s\n' "$*"
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

FILES=(
  "bots/revenue_brain_v1.py"
  "bots/revenue_exec_router_v1.py"
  "bots/revenue_lp_publish_v1.py"
  "bots/revenue_metrics_sync_v1.py"
  "bots/revenue_winner_judge_v1.py"
  "bots/revenue_improvement_loop_v1.py"
  "deploy/fortune/worker/worker.js"
  "deploy/fortune/worker/schema.sql"
  "ops/telegram_exec/run_python.sh"
)

log "checking target files"
for file in "${FILES[@]}"; do
  require_file "$file"
done

log "checking static revenue flow guards"
require_pattern "REVENUE_CORE" "bots/revenue_brain_v1.py"
require_pattern "mode=lpgen_exec" "bots/revenue_exec_router_v1.py"
require_pattern "mode=lpgen_exec" "bots/revenue_improvement_loop_v1.py"
require_pattern "tmp_exec/lp_\\*.txt" "bots/revenue_lp_publish_v1.py"
require_pattern "revenue_page_views" "bots/revenue_metrics_sync_v1.py"
require_pattern "revenue_page_views" "deploy/fortune/worker/worker.js"
require_pattern "create table if not exists revenue_page_views" "deploy/fortune/worker/schema.sql"

if rg -n "runbook_gen_exec" \
  "$ROOT/bots/revenue_brain_v1.py" \
  "$ROOT/bots/revenue_exec_router_v1.py" \
  "$ROOT/bots/revenue_improvement_loop_v1.py"; then
  log "revenue core unexpectedly routes to runbook_gen_exec"
  exit 1
fi

log "known runbook_gen_exec routes outside revenue core"
rg -n "runbook_gen_exec" \
  "$ROOT/bots/kaikun04_router_worker_v1.py" \
  "$ROOT/bots/winner_exec_bridge_v1.py" \
  "$ROOT/bots/focus3_exec_bridge_v1.py" \
  "$ROOT/ops/telegram_exec/run_python.sh" || true

log "compiling revenue python files"
python3 -m py_compile \
  "$ROOT/bots/revenue_brain_v1.py" \
  "$ROOT/bots/revenue_exec_router_v1.py" \
  "$ROOT/bots/revenue_lp_publish_v1.py" \
  "$ROOT/bots/revenue_metrics_sync_v1.py" \
  "$ROOT/bots/revenue_winner_judge_v1.py" \
  "$ROOT/bots/revenue_improvement_loop_v1.py"

if command -v node >/dev/null 2>&1; then
  log "checking worker.js syntax"
  node --check "$ROOT/deploy/fortune/worker/worker.js"
else
  log "skip worker.js syntax check: node not found"
fi

log "creating isolated smoke database"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.executescript("""
create table router_tasks (
  id integer primary key autoincrement,
  source_command_id integer default 0,
  parent_task_id integer,
  task_role text,
  target_bot text,
  mode text,
  status text,
  task_text text,
  reply_text text,
  result_text text,
  created_at text,
  updated_at text
);

create table revenue_opportunities (
  id integer primary key autoincrement,
  source text not null default 'smoke',
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

create table revenue_experiments (
  id integer primary key autoincrement,
  opportunity_id integer,
  experiment_type text not null default '',
  title text not null,
  hypothesis text not null default '',
  validation_method text not null default '',
  expected_signal text not null default '',
  expected_cost integer not null default 0,
  expected_validation_hours integer not null default 24,
  status text not null default 'new',
  router_task_id integer,
  artifact_path text not null default '',
  result_summary text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table revenue_metrics (
  id integer primary key autoincrement,
  experiment_id integer not null,
  metric_name text not null,
  metric_value real not null default 0,
  source text not null default '',
  captured_at text not null default (datetime('now'))
);

create table revenue_learnings (
  id integer primary key autoincrement,
  experiment_id integer,
  opportunity_id integer,
  learning_type text not null default '',
  summary text not null,
  evidence text not null default '',
  action text not null default '',
  confidence integer not null default 0,
  created_at text not null default (datetime('now'))
);

insert into revenue_opportunities
(title, total_score, status, rationale)
values ('smoke revenue opportunity', 100, 'new', 'smoke test');

insert into revenue_experiments
(opportunity_id, experiment_type, title, hypothesis, validation_method, expected_signal, status)
values (1, 'lp', 'smoke lp experiment', 'LP improves CTA', 'page view and CTA check', 'views', 'new');
""")
db.commit()
db.close()
PY

log "running brain -> exec router on isolated database"
python3 "$ROOT/bots/revenue_brain_v1.py"
python3 "$ROOT/bots/revenue_exec_router_v1.py"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
rows = db.execute("""
select id, parent_task_id, target_bot, mode, status, task_text
from router_tasks
order by id asc
""").fetchall()
exec_rows = [r for r in rows if r["target_bot"] == "ops_exec"]
assert exec_rows, "missing ops_exec route"
assert any("mode=lpgen_exec" in r["task_text"] for r in exec_rows), "missing lpgen_exec route"
assert not any("mode=runbook_gen_exec" in r["task_text"] for r in exec_rows), "unexpected runbook route"
exp = db.execute("select status, router_task_id from revenue_experiments where id=1").fetchone()
assert exp["status"] == "routed", exp["status"]
assert exp["router_task_id"], "missing router_task_id"
db.close()
print("[revenue_smoke] route assertion ok")
PY

log "running lp publish in isolated workdir"
mkdir -p "$WORKDIR/tmp_exec"
printf '[LPGEN]\ntask: smoke\nCTA smoke\n' > "$WORKDIR/tmp_exec/lp_smoke.txt"
(
  cd "$WORKDIR"
  python3 "$ROOT/bots/revenue_lp_publish_v1.py"
)
test -f "$WORKDIR/public_preview/revenue_lp/lp_smoke.html"

log "running winner judge -> improvement loop on isolated database"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.execute("""
update revenue_experiments
set artifact_path='public_preview/revenue_lp/lp_smoke.html',
    status='routed'
where id=1
""")
db.commit()
db.close()
PY

python3 "$ROOT/bots/revenue_winner_judge_v1.py"
python3 "$ROOT/bots/revenue_improvement_loop_v1.py"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
exp = db.execute("select status from revenue_experiments where id=1").fetchone()
metric_count = db.execute("select count(*) as c from revenue_metrics").fetchone()["c"]
learning_count = db.execute("select count(*) as c from revenue_learnings").fetchone()["c"]
improve_task = db.execute("""
select task_text
from router_tasks
where target_bot='ops_exec'
  and mode='EXEC'
  and task_text like '%REVENUE_CORE_IMPROVE%'
order by id desc
limit 1
""").fetchone()
assert exp["status"] == "improving", exp["status"]
assert metric_count >= 1, metric_count
assert learning_count >= 1, learning_count
assert improve_task and "mode=lpgen_exec" in improve_task["task_text"], "missing lpgen improve task"
db.close()
print("[revenue_smoke] winner/improvement assertion ok")
PY

log "dry-run complete; production DB and remote D1 were not modified"
