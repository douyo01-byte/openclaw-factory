#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
DB="$TMP_DIR/dev_autopilot_v1.sqlite"
OUT="$TMP_DIR/prompt.out"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

sqlite3 "$DB" < "$ROOT/sql/dev_autopilot_v1.sql"

sqlite3 "$DB" <<'SQL'
create table codex_review_queue (
  id integer primary key autoincrement,
  source_task_id integer not null default 0,
  review_status text not null default 'queued',
  candidate_score real not null default 0,
  review_summary text not null default '',
  next_prompt text not null default '',
  created_codex_task_id integer not null default 0,
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now'))
);

create table revenue_experiments (
  id integer primary key autoincrement,
  status text not null default 'new',
  experiment_type text not null default '',
  title text not null default '',
  expected_cost integer not null default 0,
  router_task_id integer,
  result_summary text not null default '',
  created_at text not null default (datetime('now'))
);

create table router_tasks (
  id integer primary key autoincrement,
  target_bot text not null default '',
  mode text not null default '',
  status text not null default 'new',
  task_text text not null default '',
  created_at text not null default (datetime('now'))
);

insert into dev_autopilot_queue (
  status,
  execution_type,
  dry_run,
  priority,
  task_text,
  safety_rules,
  target_files,
  suggested_commands,
  source_table,
  source_id
) values (
  'approved',
  'dry-run',
  1,
  90,
  'Review revenue experiment id=2 and prepare an observation-only Codex plan. Do not execute the plan.',
  'Only inspect temp DB rows in this smoke test.',
  'bots/dev_autopilot_v1.py\nsql/dev_autopilot_v1.sql',
  'python3 -m py_compile bots/dev_autopilot_v1.py',
  'revenue_experiments',
  2
);

insert into codex_review_queue (
  source_task_id,
  review_status,
  candidate_score,
  review_summary,
  next_prompt
) values (
  3,
  'approved',
  105.0,
  'dry-run review candidate; no files changed',
  'verify and report current status'
);

insert into revenue_experiments (
  status,
  experiment_type,
  title,
  expected_cost,
  router_task_id,
  result_summary
) values (
  'new',
  'observation_only',
  '既存LP改善版の反応シグナルを送信なしで確認する',
  0,
  null,
  'planning record only'
);

insert into router_tasks (
  target_bot,
  mode,
  status,
  task_text
) values (
  'kaikun04',
  'THINK',
  'deferred',
  '[WINNER_ONLY] observe only'
);
SQL

python3 "$ROOT/bots/dev_autopilot_v1.py" --db-path "$DB" > "$OUT"

grep -q "OpenClaw Dev Autopilot v1 queue_id=1" "$OUT"
grep -q "execution_type=dry-run" "$OUT"
grep -q "Do not launch Codex automatically" "$OUT"
grep -q "revenue_experiments id=1 status=new" "$OUT"
grep -q "codex_review_queue:" "$OUT"

if grep -Eiq 'api[_-]?key|token|secret|password|authorization|bearer|webhook' "$OUT"; then
  echo "FAIL: prompt leaked sensitive marker" >&2
  exit 1
fi

echo "PASS: dev_autopilot_v1 smoke"
