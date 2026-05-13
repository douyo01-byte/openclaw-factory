#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/telegram_execution_digest_v2.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
DB="$TMP_DIR/digest.db"
OUT="$TMP_DIR/digest.out"

echo "[telegram_execution_digest_v2_smoke] checking syntax"
"$PYTHON" -m py_compile bots/telegram_digest_v1.py
bash -n scripts/run_telegram_digest_v1.sh

echo "[telegram_execution_digest_v2_smoke] creating temp router_tasks"
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

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, clean_prompt, reply_text, result_text, created_at, updated_at)
values
(1, 0, 'instruction', 'kaikun04', 'AUTO', 'done',
 'Revenue LPのCTR改善を最小差分で実装し、smokeを通す',
 'Revenue LP CTR improvement with smoke',
 'routed to ops_exec',
 '',
 datetime('now', '-2 minutes'), datetime('now', '-2 minutes'));

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, reply_text, result_text, validation_reason, exec_bridge_reason, created_at, updated_at)
values
(2, 1, 'execution', 'ops_exec', 'EXEC', 'done',
 '[EXEC]' || char(10) || 'script=run_python.sh' || char(10) || 'arg=mode=lpgen_exec;task=generate LP artifact',
 'completed public_preview/revenue/lp_a.html',
 'generated artifact public_preview/revenue/lp_a.html and py_compile OK',
 '',
 '',
 datetime('now', '-1 minutes'), datetime('now', '-1 minutes'));

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, reply_text, result_text, validation_reason, exec_bridge_reason, created_at, updated_at)
values
(3, 1, 'execution', 'ops_exec', 'EXEC', 'failed',
 '[EXEC]' || char(10) || 'script=run_python.sh' || char(10) || 'arg=mode=auto_task;task=legacy path',
 'unknown mode:auto_task',
 '',
 'unknown mode:auto_task',
 '',
 datetime('now', '-1 minutes'), datetime('now', '-1 minutes'));

insert into router_tasks
(id, parent_task_id, task_role, target_bot, mode, status, task_text, reply_text, created_at, updated_at)
values
(4, 0, 'digest', 'telegram_digest', 'DIGEST', 'done',
 '[REVENUE_BANDIT_DIGEST] group_id=1 noisy housekeeping',
 'REVENUE_BANDIT_DIGEST_READY',
 datetime('now'), datetime('now'));
SQL

echo "[telegram_execution_digest_v2_smoke] running dry-run digest"
DB_PATH="$DB" OCLAW_DB_PATH="$DB" FACTORY_DB_PATH="$DB" TELEGRAM_DIGEST_DRY_RUN=1 TELEGRAM_DIGEST_WINDOW_MIN=60 "$PYTHON" -m bots.telegram_digest_v1 > "$OUT"
cat "$OUT"

echo "[telegram_execution_digest_v2_smoke] validating narrative output"
rg -n "OpenClaw execution digest" "$OUT" >/dev/null
rg -n "instruction:" "$OUT" >/dev/null
rg -n "execution:" "$OUT" >/dev/null
rg -n "result:" "$OUT" >/dev/null
rg -n "next:" "$OUT" >/dev/null
rg -n "risk:" "$OUT" >/dev/null
rg -n "public_preview/revenue/lp_a.html" "$OUT" >/dev/null
rg -n "noise: 1 digest/report housekeeping tasks compressed" "$OUT" >/dev/null
rg -n "unknown mode" "$OUT" >/dev/null

if sqlite3 "$DB" "select count(*) from telegram_digest_state where key='last_router_task_id';" | rg -v "^0$"; then
  echo "dry-run unexpectedly advanced digest state" >&2
  exit 1
fi

echo "[telegram_execution_digest_v2_smoke] complete"
