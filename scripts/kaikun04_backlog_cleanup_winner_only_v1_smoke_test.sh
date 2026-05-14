#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT_DIR/scripts/kaikun04_backlog_cleanup_winner_only_v1.sh"
TMP_DIR="$(mktemp -d)"
DB_PATH="$TMP_DIR/openclaw_smoke.db"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_eq() {
  local expected="$1"
  local actual="$2"
  local label="$3"

  if [[ "$actual" != "$expected" ]]; then
    fail "$label: expected '$expected', got '$actual'"
  fi
}

sqlite3 "$DB_PATH" <<'SQL'
create table router_tasks (
  id integer primary key,
  mode text,
  target_bot text,
  task_text text,
  intent text,
  task_role text,
  clean_prompt text,
  result_text text,
  reply_text text,
  status text,
  updated_at text
);

insert into router_tasks (id, mode, target_bot, task_text, status) values
  (1, 'THINK', 'kaikun04', 'WINNER_ONLY duplicate cleanup', 'new'),
  (2, 'THINK', 'kaikun04', ' WINNER_ONLY duplicate cleanup ', 'new'),
  (3, 'THINK', 'kaikun04', 'WINNER_ONLY solo cleanup', 'new');

insert into router_tasks (id, mode, target_bot, task_text, clean_prompt, status) values
  (4, 'THINK', 'kaikun04', 'WINNER_ONLY planner keep', 'planner', 'new'),
  (5, 'THINK', 'kaikun04', 'WINNER_ONLY planner keep', 'planner', 'new'),
  (6, 'THINK', 'kaikun04', 'WINNER_ONLY cto keep', 'cto', 'new'),
  (7, 'THINK', 'kaikun04', 'WINNER_ONLY cto keep', 'cto', 'new'),
  (8, 'THINK', 'kaikun04', 'WINNER_ONLY goal_impl keep', 'goal_impl', 'new'),
  (9, 'THINK', 'kaikun04', 'WINNER_ONLY goal_impl keep', 'goal_impl', 'new'),
  (10, 'THINK', 'kaikun04', 'WINNER_ONLY exec keep', 'exec', 'new'),
  (11, 'THINK', 'kaikun04', 'WINNER_ONLY exec keep', 'exec', 'new'),
  (12, 'THINK', 'kaikun04', 'WINNER_ONLY status_core keep', 'status_core', 'new'),
  (13, 'THINK', 'kaikun04', 'WINNER_ONLY status_core keep', 'status_core', 'new'),
  (14, 'THINK', 'kaikun04', 'WINNER_ONLY codex keep', 'codex', 'new'),
  (15, 'THINK', 'kaikun04', 'WINNER_ONLY codex keep', 'codex', 'new'),
  (16, 'THINK', 'kaikun04', 'WINNER_ONLY revenue keep', 'revenue', 'new'),
  (17, 'THINK', 'kaikun04', 'WINNER_ONLY revenue keep', 'revenue', 'new'),
  (18, 'THINK', 'kaikun04', 'WINNER_ONLY trend keep', 'trend', 'new'),
  (19, 'THINK', 'kaikun04', 'WINNER_ONLY trend keep', 'trend', 'new');

insert into router_tasks (id, mode, target_bot, task_text, status) values
  (20, 'EXEC', 'kaikun04', 'WINNER_ONLY duplicate cleanup', 'new'),
  (21, 'THINK', 'kaikun02', 'WINNER_ONLY duplicate cleanup', 'new'),
  (22, 'THINK', 'kaikun04', 'regular duplicate cleanup', 'new'),
  (23, 'THINK', 'kaikun04', 'regular duplicate cleanup', 'new'),
  (24, 'THINK', 'kaikun04', 'WINNER_ONLY duplicate cleanup', 'done');
SQL

dry_output="$(DB_PATH="$DB_PATH" LIMIT=100 bash "$SCRIPT")"

eligible_total="$(awk -F'|' '$1 == "eligible_total" { print $2 }' <<<"$dry_output")"
selected_limited="$(awk -F'|' '$1 == "selected_limited" { print $2 }' <<<"$dry_output")"
deferred_after_dry_run="$(sqlite3 "$DB_PATH" "select count(*) from router_tasks where status = 'deferred';")"

assert_eq "1" "$eligible_total" "dry-run eligible_total"
assert_eq "1" "$selected_limited" "dry-run selected_limited"
assert_eq "0" "$deferred_after_dry_run" "dry-run deferred rows"

apply_output="$(DB_PATH="$DB_PATH" APPLY=1 LIMIT=1 bash "$SCRIPT")"
updated="$(awk -F'=' '$1 == "updated" { print $2 }' <<<"$apply_output")"
deferred_after_apply="$(sqlite3 "$DB_PATH" "select count(*) from router_tasks where status = 'deferred';")"
deferred_id="$(sqlite3 "$DB_PATH" "select id from router_tasks where status = 'deferred';")"

assert_eq "1" "$updated" "apply updated count"
assert_eq "1" "$deferred_after_apply" "apply deferred rows"
assert_eq "2" "$deferred_id" "apply deferred duplicate id"

echo "PASS: kaikun04 backlog cleanup WINNER_ONLY smoke"
