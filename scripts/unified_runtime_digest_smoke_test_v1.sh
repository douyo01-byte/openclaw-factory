#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/unified_runtime_digest_v1.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
DB="$TMP_DIR/unified_runtime_digest.db"
OUT="$TMP_DIR/unified_runtime_digest.out"

echo "[unified_runtime_digest_smoke] checking syntax"
"$PYTHON" -m py_compile bots/unified_runtime_digest_v1.py
bash -n scripts/unified_runtime_digest_smoke_test_v1.sh

echo "[unified_runtime_digest_smoke] creating temp schema"
sqlite3 "$DB" < migrations/20260513_unified_runtime_digest_v1.sql
sqlite3 "$DB" <<'SQL'
create table router_tasks (
  id integer primary key autoincrement,
  parent_task_id integer default 0,
  task_role text default '',
  target_bot text default '',
  mode text default '',
  status text default 'new',
  task_text text default '',
  clean_prompt text default '',
  reply_text text default '',
  result_text text default '',
  validation_reason text default '',
  exec_bridge_reason text default '',
  created_at text default (datetime('now')),
  updated_at text default (datetime('now'))
);

create table runtime_health_scores (
  id integer primary key autoincrement,
  program_key text not null,
  launchd_label text not null default '',
  category text not null default '',
  classification text not null default '',
  entropy_score real not null default 0,
  usefulness_score real not null default 0,
  zombie_score real not null default 0,
  observability_score real not null default 0,
  stability_score real not null default 0,
  core_weight real not null default 0,
  log_pressure_score real not null default 0,
  cleanup_priority real not null default 0,
  health_score real not null default 0,
  score_reason text not null default '',
  created_at text default (datetime('now'))
);

create table runtime_pause_candidates (
  id integer primary key autoincrement,
  program_key text not null,
  launchd_label text not null default '',
  approval_status text not null default 'queued',
  risk_level text not null default 'medium',
  reason text not null default '',
  created_at text default (datetime('now'))
);

create table codex_tasks (
  id integer primary key autoincrement,
  status text not null default 'new',
  updated_at text default (datetime('now'))
);

create table codex_task_runs (
  id integer primary key autoincrement,
  task_id integer not null default 0,
  status text not null default 'review',
  result_summary text not null default ''
);

create table codex_review_queue (
  id integer primary key autoincrement,
  source_task_id integer not null default 0,
  review_status text not null default 'queued',
  candidate_score real not null default 0
);

create table revenue_experiments (
  id integer primary key autoincrement,
  status text not null default 'new'
);

create table revenue_learnings (
  id integer primary key autoincrement,
  learning_key text not null default ''
);

create table revenue_variant_groups (
  id integer primary key autoincrement,
  status text not null default 'active'
);

create table trend_items (
  id integer primary key autoincrement,
  source text not null default 'github',
  item_url text not null default ''
);

create table trend_proposals (
  id integer primary key autoincrement,
  proposal_status text not null default 'queued',
  proposal_text text not null default ''
);

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, clean_prompt, reply_text, result_text, created_at, updated_at)
values
(1, 0, 'instruction', 'kaikun04', 'AUTO', 'done',
 'Revenue LPのCTR改善を最小差分で実装し、smokeを通す',
 'Revenue LP CTR improvement with smoke',
 'routed to ops_exec',
 '',
 datetime('now', '-4 minutes'), datetime('now', '-4 minutes'));

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, reply_text, result_text, created_at, updated_at)
values
(2, 1, 'execution', 'ops_exec', 'EXEC', 'done',
 '[EXEC]' || char(10) || 'script=run_python.sh' || char(10) || 'arg=mode=lpgen_exec;task=generate LP artifact',
 'completed public_preview/revenue/lp_a.html',
 'generated artifact public_preview/revenue/lp_a.html and py_compile OK',
 datetime('now', '-3 minutes'), datetime('now', '-3 minutes'));

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, reply_text, validation_reason, created_at, updated_at)
values
(3, 1, 'execution', 'ops_exec', 'EXEC', 'failed',
 '[EXEC]' || char(10) || 'script=run_python.sh' || char(10) || 'arg=mode=auto_task;task=legacy path',
 'unknown mode:auto_task',
 'unknown mode:auto_task',
 datetime('now', '-2 minutes'), datetime('now', '-2 minutes'));

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, reply_text, created_at, updated_at)
values
(4, 0, 'digest', 'telegram_digest', 'DIGEST', 'done',
 '[REVENUE_BANDIT_DIGEST] noisy housekeeping',
 'REVENUE_BANDIT_DIGEST_READY',
 datetime('now', '-1 minutes'), datetime('now', '-1 minutes'));

insert into runtime_health_scores
(program_key, launchd_label, category, classification, entropy_score, usefulness_score, zombie_score, observability_score, stability_score, core_weight, log_pressure_score, cleanup_priority, health_score, score_reason)
values
('task_router_v1', 'jp.openclaw.task_router_v1', 'router', 'KEEP', 20, 90, 0, 80, 85, 100, 10, 5, 82, 'core router stable'),
('telegram_report_v1', 'jp.openclaw.telegram_report_v1', 'telegram', 'PAUSE_CANDIDATE', 72, 18, 82, 40, 35, 0, 88, 86, 28, 'low value repeated notifications');

insert into runtime_pause_candidates
(program_key, launchd_label, approval_status, risk_level, reason)
values
('telegram_report_v1', 'jp.openclaw.telegram_report_v1', 'queued', 'low', 'low value repeated notifications');

insert into codex_tasks(status) values ('review'), ('done');
insert into codex_task_runs(task_id, status, result_summary) values (1, 'review', 'smoke result waiting for review');
insert into codex_review_queue(source_task_id, review_status, candidate_score) values (1, 'queued', 42);

insert into revenue_experiments(status) values ('running'), ('winner_candidate');
insert into revenue_learnings(learning_key) values ('winning_cta');
insert into revenue_variant_groups(status) values ('active');

insert into trend_items(source, item_url) values ('github', 'https://github.com/example/tool');
insert into trend_proposals(proposal_status, proposal_text) values ('queued', 'Evaluate safe OSS reuse');
SQL

echo "[unified_runtime_digest_smoke] running dry-run digest"
DB_PATH="$DB" UNIFIED_RUNTIME_DIGEST_DRY_RUN=1 UNIFIED_RUNTIME_DIGEST_WINDOW_MIN=60 "$PYTHON" -m bots.unified_runtime_digest_v1 --dry-run > "$OUT"
cat "$OUT"

echo "[unified_runtime_digest_smoke] validating digest output"
rg -n "OpenClaw unified runtime digest" "$OUT" >/dev/null
rg -n "Execution:" "$OUT" >/dev/null
rg -n "Runtime health:" "$OUT" >/dev/null
rg -n "Cleanup:" "$OUT" >/dev/null
rg -n "Codex:" "$OUT" >/dev/null
rg -n "Revenue:" "$OUT" >/dev/null
rg -n "Trend:" "$OUT" >/dev/null
rg -n "Residual risk:" "$OUT" >/dev/null
rg -n "public_preview/revenue/lp_a.html" "$OUT" >/dev/null
rg -n "noise: 1 digest/report housekeeping tasks compressed" "$OUT" >/dev/null
rg -n "telegram_report_v1" "$OUT" >/dev/null
rg -n "review_queue: queued=1" "$OUT" >/dev/null
rg -n "experiments: running=1 / winner_candidate=1" "$OUT" >/dev/null
rg -n "proposals: queued=1" "$OUT" >/dev/null
rg -n "EXEC mode routing risk" "$OUT" >/dev/null
rg -n "runtime cleanup queue requires review" "$OUT" >/dev/null

if sqlite3 "$DB" "select count(*) from unified_runtime_digests;" | rg -v "^0$"; then
  echo "dry-run unexpectedly recorded unified digest" >&2
  exit 1
fi

if rg -n "launchctl|git add|git commit|git push|deploy|urllib|requests|oclibs\\.telegram|send_tg" bots/unified_runtime_digest_v1.py; then
  echo "unexpected external action surface in unified digest bot" >&2
  exit 1
fi

echo "[unified_runtime_digest_smoke] complete"
