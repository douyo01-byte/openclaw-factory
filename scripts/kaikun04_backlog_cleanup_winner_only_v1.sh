#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${DB_PATH:-"$ROOT_DIR/data/openclaw.db"}"
LIMIT="${LIMIT:-100}"
APPLY="${APPLY:-0}"

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "error: sqlite3 not found" >&2
  exit 1
fi

if [[ ! -f "$DB_PATH" ]]; then
  echo "error: DB_PATH not found: $DB_PATH" >&2
  exit 1
fi

if ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || [[ "$LIMIT" -lt 1 ]]; then
  echo "error: LIMIT must be a positive integer" >&2
  exit 1
fi

if [[ "$APPLY" != "0" && "$APPLY" != "1" ]]; then
  echo "error: APPLY must be 0 or 1" >&2
  exit 1
fi

read -r -d '' BASE_CTE <<'SQL' || true
with raw_candidates as (
  select
    id,
    lower(
      coalesce(mode, '') || ' ' ||
      coalesce(target_bot, '') || ' ' ||
      coalesce(task_text, '') || ' ' ||
      coalesce(intent, '') || ' ' ||
      coalesce(task_role, '') || ' ' ||
      coalesce(clean_prompt, '') || ' ' ||
      coalesce(result_text, '') || ' ' ||
      coalesce(reply_text, '')
    ) as task_blob,
    row_number() over (
      partition by lower(trim(task_text))
      order by id asc
    ) as duplicate_rank
  from router_tasks
  where status = 'new'
    and mode = 'THINK'
    and target_bot = 'kaikun04'
    and task_text like '%WINNER_ONLY%'
),
candidates as (
  select id, duplicate_rank
  from raw_candidates
  where task_blob not like '%planner%'
    and task_blob not like '%cto%'
    and task_blob not like '%goal_impl%'
    and task_blob not like '%exec%'
    and task_blob not like '%status_core%'
    and task_blob not like '%codex%'
    and task_blob not like '%revenue%'
    and task_blob not like '%trend%'
),
targets as (
  select id
  from candidates
  where duplicate_rank > 1
),
limited_targets as (
  select id
  from targets
  order by id asc
  limit :limit
)
SQL

echo "mode=$([[ "$APPLY" == "1" ]] && echo apply || echo dry-run)"
echo "db=$DB_PATH"
echo "limit=$LIMIT"

sqlite3 -cmd ".parameter init" -cmd ".parameter set :limit $LIMIT" "$DB_PATH" "${BASE_CTE}
select 'eligible_total', count(*) from targets
union all
select 'selected_limited', count(*) from limited_targets;"

if [[ "$APPLY" != "1" ]]; then
  echo "dry-run only: no rows updated"
  exit 0
fi

UPDATED="$(
  sqlite3 -cmd ".parameter init" -cmd ".parameter set :limit $LIMIT" "$DB_PATH" "${BASE_CTE}
update router_tasks
set status = 'deferred',
    updated_at = datetime('now')
where id in (select id from limited_targets);
select changes();"
)"

echo "updated=$UPDATED"
