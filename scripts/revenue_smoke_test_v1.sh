#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
DB_PATH="$WORKDIR/revenue_smoke.sqlite3"
export DB_PATH
export REVENUE_SMOKE_WORKDIR="$WORKDIR"

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
  "bots/revenue_bandit_v1.py"
  "bots/revenue_distribution_executor_v1.py"
  "bots/revenue_publish_approval_server_v1.py"
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
require_pattern "revenue_variant_groups" "bots/revenue_bandit_v1.py"
require_pattern "revenue_variant_metrics" "bots/revenue_bandit_v1.py"
require_pattern "revenue_strategy_scores" "bots/revenue_bandit_v1.py"
require_pattern "revenue_economic_metrics" "bots/revenue_bandit_v1.py"
require_pattern "revenue_real_orders" "bots/revenue_bandit_v1.py"
require_pattern "revenue_capital_allocations" "bots/revenue_bandit_v1.py"
require_pattern "revenue_business_domains" "bots/revenue_bandit_v1.py"
require_pattern "revenue_capital_migrations" "bots/revenue_bandit_v1.py"
require_pattern "revenue_distribution_tasks" "bots/revenue_exec_router_v1.py"
require_pattern "public_preview/revenue_distribution" "bots/revenue_distribution_executor_v1.py"
require_pattern "127.0.0.1" "bots/revenue_publish_approval_server_v1.py"
require_pattern "mode=lpgen_exec" "bots/revenue_improvement_loop_v1.py"
require_pattern "tmp_exec/lp_\\*.txt" "bots/revenue_lp_publish_v1.py"
require_pattern "revenue_page_views" "bots/revenue_metrics_sync_v1.py"
require_pattern "revenue_page_views" "deploy/fortune/worker/worker.js"
require_pattern "event_type" "deploy/fortune/worker/worker.js"
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
  "$ROOT/bots/revenue_bandit_v1.py" \
  "$ROOT/bots/revenue_distribution_executor_v1.py" \
  "$ROOT/bots/revenue_publish_approval_server_v1.py" \
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
  domain_key text not null default 'general',
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

create table revenue_page_views (
  id integer primary key autoincrement,
  path text not null,
  event_type text not null default 'page_view',
  variant_id text not null default '',
  traffic_source text not null default '',
  referer text not null default '',
  ua text not null default '',
  ip_hash text not null default '',
  created_at text not null
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

create table revenue_distribution_publish_queue (
  id integer primary key autoincrement,
  distribution_task_id integer not null unique,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  distribution_type text not null default '',
  traffic_source text not null default '',
  artifact_path text not null default '',
  candidate_score real not null default 0,
  publish_status text not null default 'queued',
  approval_note text not null default '',
  queued_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
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

create table revenue_economic_metrics (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  estimated_cac real not null default 0,
  estimated_ltv real not null default 0,
  payback_speed real not null default 0,
  infra_cost real not null default 0,
  human_cost real not null default 0,
  automation_savings real not null default 0,
  expected_profit real not null default 0,
  profit_efficiency real not null default 0,
  economic_multiplier real not null default 1,
  suppressed integer not null default 0,
  source text not null default '',
  captured_at text not null default (datetime('now')),
  unique(group_id, experiment_id)
);

create table revenue_real_orders (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  variant_key text not null default '',
  order_id text not null,
  revenue real not null default 0,
  gross_profit real not null default 0,
  refund_risk real not null default 0,
  fulfillment_cost real not null default 0,
  support_cost real not null default 0,
  net_profit real not null default 0,
  recovered_days real not null default 0,
  source text not null default 'local_ingest',
  created_at text not null default (datetime('now')),
  unique(order_id)
);

create table revenue_capital_allocations (
  id integer primary key autoincrement,
  opportunity_id integer not null unique,
  allocated_budget real not null default 0,
  allocated_compute real not null default 0,
  allocated_time real not null default 0,
  expected_roi real not null default 0,
  realized_roi real not null default 0,
  capital_score real not null default 0,
  risk_score real not null default 0,
  liquidity_score real not null default 100,
  source text not null default 'local_simulation',
  updated_at text not null default (datetime('now'))
);

create table revenue_business_domains (
  id integer primary key autoincrement,
  domain_key text not null unique,
  domain_type text not null default '',
  capital_allocated real not null default 0,
  revenue_generated real not null default 0,
  net_profit real not null default 0,
  volatility_score real not null default 0,
  scalability_score real not null default 50,
  automation_fit real not null default 50,
  moat_score real not null default 0,
  source text not null default 'local_simulation',
  updated_at text not null default (datetime('now'))
);

create table revenue_capital_migrations (
  id integer primary key autoincrement,
  from_domain text not null,
  to_domain text not null,
  migration_reason text not null default '',
  migrated_budget real not null default 0,
  migrated_compute real not null default 0,
  expected_gain real not null default 0,
  realized_gain real not null default 0,
  migration_score real not null default 0,
  source text not null default 'local_simulation',
  created_at text not null default (datetime('now')),
  unique(from_domain, to_domain, migration_reason)
);

create table revenue_strategy_scores (
  id integer primary key autoincrement,
  group_id integer not null,
  experiment_id integer not null,
  horizon_type text not null,
  ctr_score real not null default 0,
  conversion_score real not null default 0,
  approval_score real not null default 0,
  revenue_efficiency real not null default 0,
  automation_score real not null default 0,
  sustainability_score real not null default 0,
  total_score real not null default 0,
  source text not null default '',
  captured_at text not null default (datetime('now')),
  unique(group_id, experiment_id, horizon_type)
);

insert into revenue_opportunities
(domain_key, title, total_score, status, rationale)
values ('ai_fortune', 'smoke revenue opportunity', 100, 'new', 'smoke test');

insert into revenue_opportunities
(domain_key, title, total_score, status, rationale)
values ('comparison_media', 'smoke low liquidity opportunity', 50, 'new', 'smoke portfolio liquidity test');

insert into revenue_experiments
(opportunity_id, experiment_type, title, hypothesis, validation_method, expected_signal, status)
values (1, 'lp', 'smoke lp experiment', 'LP improves CTA', 'page view and CTA check', 'views', 'new');

insert into revenue_business_domains
(domain_key, domain_type, capital_allocated, revenue_generated, net_profit, volatility_score, scalability_score, automation_fit, moat_score, source, updated_at)
values
('ai_fortune', 'digital_goods', 25, 0, 0, 20, 85, 90, 55, 'smoke_domain', datetime('now')),
('comparison_media', 'affiliate_seo', 100, 0, 0, 90, 60, 35, 20, 'smoke_high_volatility', datetime('now')),
('micro_saas', 'micro_saas', 50, 0, 0, 45, 75, 70, 65, 'smoke_extra_domain', datetime('now'));

insert into revenue_capital_allocations
(opportunity_id, allocated_budget, allocated_compute, allocated_time, expected_roi, risk_score, liquidity_score, source, updated_at)
values
(1, 25, 2, 4, 2.0, 15, 85, 'smoke_allocation', datetime('now')),
(2, 100, 20, 40, 0.5, 70, 10, 'smoke_low_liquidity', datetime('now'));
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
assert len(exec_rows) >= 3, "missing bandit variant routes"
assert any("mode=lpgen_exec" in r["task_text"] for r in exec_rows), "missing lpgen_exec route"
assert not any("mode=runbook_gen_exec" in r["task_text"] for r in exec_rows), "unexpected runbook route"
group_count = db.execute("select count(*) as c from revenue_variant_groups").fetchone()["c"]
variant_count = db.execute("select count(*) as c from revenue_variant_metrics").fetchone()["c"]
dist_count = db.execute("select count(*) as c from revenue_distribution_tasks").fetchone()["c"]
assert group_count == 1, group_count
assert variant_count == 3, variant_count
assert dist_count == 15, dist_count
bad_links = db.execute("""
select count(*) as c
from revenue_distribution_tasks
where cta_url not like '%variant_id=%'
   or cta_url not like '%traffic_source=%'
""").fetchone()["c"]
assert bad_links == 0, bad_links
exp = db.execute("select status, router_task_id from revenue_experiments where id=1").fetchone()
assert exp["status"] == "routed", exp["status"]
assert exp["router_task_id"], "missing router_task_id"
db.close()
print("[revenue_smoke] route assertion ok")
PY

log "running distribution executor in isolated workdir"
(
  cd "$WORKDIR"
  python3 "$ROOT/bots/revenue_distribution_executor_v1.py"
)

python3 - <<'PY'
import os
import sqlite3
from pathlib import Path

workdir = Path(os.environ["REVENUE_SMOKE_WORKDIR"])
db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
rows = db.execute("""
select artifact_path, cta_url
from revenue_distribution_tasks
where status='generated'
""").fetchall()
queue_count = db.execute("select count(*) as c from revenue_distribution_publish_queue where publish_status='queued'").fetchone()["c"]
top = db.execute("""
select candidate_score
from revenue_distribution_publish_queue
order by candidate_score desc, id asc
limit 1
""").fetchone()
assert len(rows) == 15, len(rows)
assert queue_count == 15, queue_count
assert top["candidate_score"] > 0, top["candidate_score"]
assert (workdir / "public_preview/revenue_distribution/index.html").exists(), "missing publish queue index"
for row in rows:
    path = Path(row["artifact_path"])
    if not path.is_absolute():
        path = workdir / path
    assert path.exists(), row["artifact_path"]
    text = path.read_text(encoding="utf-8")
    assert "variant_id=" in row["cta_url"], row["cta_url"]
    assert "traffic_source=" in row["cta_url"], row["cta_url"]
    assert "cta_url:" in text, text
db.close()
print("[revenue_smoke] distribution artifacts ok")
PY

log "running approval flow dry-run"
python3 - <<'PY'
import os
import sqlite3

from bots import revenue_publish_approval_server_v1 as approval

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
ids = [
    r["id"]
    for r in db.execute("""
        select id
        from revenue_distribution_publish_queue
        order by candidate_score desc, id asc
        limit 2
    """).fetchall()
]
db.close()
assert len(ids) == 2, ids
assert approval.update_status(ids[0], "approved", "smoke approve")
assert approval.update_status(ids[1], "rejected", "smoke reject")
html = approval.render_page()
assert "approved" in html and "rejected" in html, html

db = sqlite3.connect(os.environ["DB_PATH"])
approved = db.execute("select count(*) from revenue_distribution_publish_queue where publish_status='approved'").fetchone()[0]
rejected = db.execute("select count(*) from revenue_distribution_publish_queue where publish_status='rejected'").fetchone()[0]
queued = db.execute("select count(*) from revenue_distribution_publish_queue where publish_status='queued'").fetchone()[0]
memory_count = db.execute("select count(*) from revenue_memory_patterns where memory_type='approved_copy'").fetchone()[0]
db.close()
assert approved == 1, approved
assert rejected == 1, rejected
assert queued == 13, queued
assert memory_count >= 1, memory_count
print("[revenue_smoke] approval flow ok")
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
rows = db.execute("select id from revenue_experiments order by id asc").fetchall()
for idx, (experiment_id,) in enumerate(rows, start=1):
    db.execute("""
    update revenue_experiments
    set artifact_path=?,
        status='routed'
    where id=?
    """, (f"public_preview/revenue_lp/lp_smoke_{idx}.html", experiment_id))
    db.execute("""
    insert into revenue_metrics
    (experiment_id, metric_name, metric_value, source, captured_at)
    values
    (?, 'artifact_score', ?, 'smoke', datetime('now'))
    """, (experiment_id, 10 + idx))
    db.execute("""
    insert into revenue_metrics
    (experiment_id, metric_name, metric_value, source, captured_at)
    values
    (?, 'cta_click', ?, 'smoke', datetime('now'))
    """, (experiment_id, idx))
    if idx == 2:
        db.execute("""
        insert into revenue_metrics
        (experiment_id, metric_name, metric_value, source, captured_at)
        values
        (?, 'human_cost', 100, 'smoke_negative_roi', datetime('now'))
        """, (experiment_id,))
    if idx == 3:
        db.execute("""
        insert into revenue_metrics
        (experiment_id, metric_name, metric_value, source, captured_at)
        values
        (?, 'estimated_ltv', 240, 'smoke_positive_roi', datetime('now'))
        """, (experiment_id,))
    if idx == 2:
        db.execute("""
        insert into revenue_real_orders
        (
          group_id,
          experiment_id,
          variant_key,
          order_id,
          revenue,
          gross_profit,
          refund_risk,
          fulfillment_cost,
          support_cost,
          net_profit,
          recovered_days,
          source
        )
        values
        (1, ?, 'B', 'smoke-order-negative', 80, 20, 0.2, 35, 15, -30, 14, 'smoke_local_ingest')
        """, (experiment_id,))
    if idx == 3:
        db.execute("""
        insert into revenue_real_orders
        (
          group_id,
          experiment_id,
          variant_key,
          order_id,
          revenue,
          gross_profit,
          refund_risk,
          fulfillment_cost,
          support_cost,
          net_profit,
          recovered_days,
          source
        )
        values
        (1, ?, 'C', 'smoke-order-positive', 240, 140, 0.05, 30, 10, 100, 3, 'smoke_local_ingest')
        """, (experiment_id,))
    path = f"public_preview/revenue_lp/lp_smoke_{idx}.html"
    variant = chr(ord("A") + idx - 1)
    source = ["telegram_post", "x_thread", "short_blog"][idx - 1]
    for i in range(idx * 10):
        db.execute("""
        insert into revenue_page_views(path, event_type, variant_id, traffic_source, created_at)
        values(?, 'page_view', ?, ?, datetime('now'))
        """, (path, variant, source))
    for _ in range(idx):
        db.execute("""
        insert into revenue_page_views(path, event_type, variant_id, traffic_source, created_at)
        values(?, 'cta_click', ?, ?, datetime('now'))
        """, (path, variant, source))
    for _ in range(max(0, idx - 1)):
        db.execute("""
        insert into revenue_page_views(path, event_type, variant_id, traffic_source, created_at)
        values(?, 'telegram_click', ?, ?, datetime('now'))
        """, (path, variant, "telegram_post"))
    if idx == 3:
        db.execute("""
        insert into revenue_page_views(path, event_type, variant_id, traffic_source, created_at)
        values(?, 'conversion', ?, ?, datetime('now'))
        """, (path, variant, source))
db.commit()
db.close()
PY

python3 "$ROOT/bots/revenue_bandit_v1.py"
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
winner_count = db.execute("select count(*) as c from revenue_variant_metrics where status='winner'").fetchone()["c"]
loser_count = db.execute("select count(*) as c from revenue_variant_loser_archive").fetchone()["c"]
digest_count = db.execute("select count(*) as c from revenue_bandit_digests").fetchone()["c"]
memory_count = db.execute("select count(*) as c from revenue_memory_patterns").fetchone()["c"]
strategy_count = db.execute("select count(*) as c from revenue_strategy_scores").fetchone()["c"]
horizon_count = db.execute("select count(distinct horizon_type) as c from revenue_strategy_scores").fetchone()["c"]
memory_horizon_count = db.execute("select count(distinct horizon_type) as c from revenue_memory_patterns").fetchone()["c"]
economic_count = db.execute("select count(*) as c from revenue_economic_metrics").fetchone()["c"]
suppressed_count = db.execute("select count(*) as c from revenue_economic_metrics where suppressed=1").fetchone()["c"]
profitable_count = db.execute("select count(*) as c from revenue_economic_metrics where expected_profit > 0").fetchone()["c"]
memory_economic_count = db.execute("select count(*) as c from revenue_memory_patterns where economic_summary != ''").fetchone()["c"]
real_order_count = db.execute("select count(*) as c from revenue_real_orders").fetchone()["c"]
real_profitable_count = db.execute("select count(*) as c from revenue_real_orders where net_profit > 0").fetchone()["c"]
real_negative_count = db.execute("select count(*) as c from revenue_real_orders where net_profit < 0").fetchone()["c"]
capital_project_count = db.execute("select count(*) as c from revenue_capital_allocations").fetchone()["c"]
low_liquidity_count = db.execute("select count(*) as c from revenue_capital_allocations where liquidity_score < 20").fetchone()["c"]
realized_roi_count = db.execute("select count(*) as c from revenue_capital_allocations where opportunity_id=1 and realized_roi > 0").fetchone()["c"]
memory_portfolio_count = db.execute("select count(*) as c from revenue_memory_patterns where portfolio_summary != ''").fetchone()["c"]
domain_count = db.execute("select count(*) as c from revenue_business_domains").fetchone()["c"]
high_volatility_count = db.execute("select count(*) as c from revenue_business_domains where volatility_score >= 80").fetchone()["c"]
high_automation_count = db.execute("select count(*) as c from revenue_business_domains where automation_fit >= 80").fetchone()["c"]
domain_profit_count = db.execute("select count(*) as c from revenue_business_domains where domain_key='ai_fortune' and net_profit > 0").fetchone()["c"]
memory_domain_count = db.execute("select count(*) as c from revenue_memory_patterns where domain_summary != ''").fetchone()["c"]
migration_count = db.execute("select count(*) as c from revenue_capital_migrations").fetchone()["c"]
migration_gain_count = db.execute("select count(*) as c from revenue_capital_migrations where expected_gain > 0 and migration_score > 0").fetchone()["c"]
migration_memory_count = db.execute("select count(*) as c from revenue_memory_patterns where domain_summary like '%migration=%'").fetchone()["c"]
real_suppressed_count = db.execute("""
select count(*) as c
from revenue_economic_metrics em
join revenue_real_orders ro on ro.experiment_id=em.experiment_id and ro.group_id=em.group_id
where ro.net_profit < 0
  and em.suppressed=1
""").fetchone()["c"]
ranked = db.execute("""
select ctr, cvr, score
from revenue_variant_metrics
where status='winner'
limit 1
""").fetchone()
digest = db.execute("""
select summary
from revenue_bandit_digests
order by id desc
limit 1
""").fetchone()
improve_task = db.execute("""
select task_text
from router_tasks
where target_bot='ops_exec'
  and mode='EXEC'
  and task_text like '%REVENUE_CORE_IMPROVE%'
order by id desc
limit 1
""").fetchone()
assert winner_count == 1, winner_count
assert loser_count >= 2, loser_count
assert digest_count >= 1, digest_count
assert ranked["ctr"] > 0, ranked["ctr"]
assert ranked["cvr"] > 0, ranked["cvr"]
assert "ctr=" in digest["summary"] and "cvr=" in digest["summary"], digest["summary"]
assert "source_ctr:" in digest["summary"], digest["summary"]
assert "distribution:" in digest["summary"], digest["summary"]
assert "publish_queue:" in digest["summary"], digest["summary"]
assert "approval_summary:" in digest["summary"], digest["summary"]
assert "publish_candidates:" in digest["summary"], digest["summary"]
assert "top_memories:" in digest["summary"], digest["summary"]
assert "strategy_horizon:" in digest["summary"], digest["summary"]
assert "short_term" in digest["summary"] and "mid_term" in digest["summary"] and "long_term" in digest["summary"], digest["summary"]
assert "economic_summary:" in digest["summary"], digest["summary"]
assert "economic:" in digest["summary"], digest["summary"]
assert "suppressed=" in digest["summary"], digest["summary"]
assert "real_commerce:" in digest["summary"], digest["summary"]
assert "real_profit=" in digest["summary"], digest["summary"]
assert "orders=" in digest["summary"], digest["summary"]
assert "portfolio:" in digest["summary"], digest["summary"]
assert "portfolio_variant:" in digest["summary"], digest["summary"]
assert "low_liquidity=" in digest["summary"], digest["summary"]
assert "domain_leaderboard:" in digest["summary"], digest["summary"]
assert "domain_variant:" in digest["summary"], digest["summary"]
assert "ai_fortune" in digest["summary"], digest["summary"]
assert "capital_migration:" in digest["summary"], digest["summary"]
assert "comparison_media->ai_fortune" in digest["summary"], digest["summary"]
assert metric_count >= 1, metric_count
assert learning_count >= 1, learning_count
assert memory_count >= 4, memory_count
assert strategy_count >= 9, strategy_count
assert horizon_count == 3, horizon_count
assert memory_horizon_count >= 2, memory_horizon_count
assert economic_count >= 3, economic_count
assert suppressed_count >= 1, suppressed_count
assert profitable_count >= 1, profitable_count
assert memory_economic_count >= 1, memory_economic_count
assert real_order_count == 2, real_order_count
assert real_profitable_count == 1, real_profitable_count
assert real_negative_count == 1, real_negative_count
assert real_suppressed_count >= 1, real_suppressed_count
assert capital_project_count >= 2, capital_project_count
assert low_liquidity_count >= 1, low_liquidity_count
assert realized_roi_count >= 1, realized_roi_count
assert memory_portfolio_count >= 1, memory_portfolio_count
assert domain_count >= 3, domain_count
assert high_volatility_count >= 1, high_volatility_count
assert high_automation_count >= 1, high_automation_count
assert domain_profit_count >= 1, domain_profit_count
assert memory_domain_count >= 1, memory_domain_count
assert migration_count >= 1, migration_count
assert migration_gain_count >= 1, migration_gain_count
assert migration_memory_count >= 1, migration_memory_count
assert improve_task and "mode=lpgen_exec" in improve_task["task_text"], "missing lpgen improve task"
db.close()
print("[revenue_smoke] winner/improvement/horizon/economic/real-commerce/capital/domain-migration assertion ok")
PY

log "checking memory reuse in next generation"
python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.execute("""
insert into revenue_experiments
(opportunity_id, experiment_type, title, hypothesis, validation_method, expected_signal, status)
values
(1, 'lp', 'memory reuse smoke', 'reuse memory improves next LP', 'dry-run', 'memory hint present', 'new')
""")
exp_id = db.execute("select last_insert_rowid()").fetchone()[0]
task_text = f"""[REVENUE_CORE]
Opportunity:
- id: 1
- title: smoke revenue opportunity
- rationale: smoke
- total_score: 100

Experiment:
- id: {exp_id}
- type: lp
- title: memory reuse smoke
- hypothesis: reuse memory improves next LP
- validation_method: dry-run
- expected_signal: memory hint present
"""
db.execute("""
insert into router_tasks(target_bot, mode, status, task_text, created_at, updated_at)
values('kaikun04', 'THINK', 'new', ?, datetime('now'), datetime('now'))
""", (task_text,))
db.commit()
db.close()
PY

python3 "$ROOT/bots/revenue_exec_router_v1.py"

python3 - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
task = db.execute("""
select task_text
from router_tasks
where target_bot='ops_exec'
  and task_text like '%memory reuse smoke%'
order by id desc
limit 1
""").fetchone()
reuse = db.execute("select max(reuse_count) as reuse_count from revenue_memory_patterns").fetchone()["reuse_count"]
dist = db.execute("""
select content
from revenue_distribution_tasks
where content like '%memory reuse smoke%'
order by id desc
limit 1
""").fetchone()
db.close()
assert task and "MEMORY_HINTS:" in task["task_text"], task["task_text"] if task else "missing task"
assert dist and "MEMORY_HINTS:" in dist["content"], dist["content"] if dist else "missing dist"
assert reuse and reuse >= 1, reuse
print("[revenue_smoke] memory reuse ok")
PY

log "dry-run complete; production DB and remote D1 were not modified"
