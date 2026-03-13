#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"

consecutive_no_new=0

run_one() {
  local out
  out=$(python "$1" 2>&1 || true)
  echo "$out"
  if echo "$out" | egrep -q 'skip=no_new_'; then
    consecutive_no_new=$((consecutive_no_new + 1))
  else
    consecutive_no_new=0
  fi
}

while true; do
  [ -f bots/innovation_llm_engine_v1.py ] && run_one bots/innovation_llm_engine_v1.py
  run_one bots/code_review_engine_v1.py
  true

  active=$(sqlite3 "$DB_PATH" "
  select count(*)
  from dev_proposals
  where status='approved'
    and coalesce(project_decision,'')='execute_now'
    and coalesce(guard_status,'')='safe';
  " 2>/dev/null || echo 0)

  echo "[supply] active_execute_now_safe=$active consecutive_no_new=$consecutive_no_new"

  if [ "${active:-0}" -lt 3 ]; then
    python bots/mainstream_fallback_supply_v1.py || true
  elif [ "$consecutive_no_new" -ge 3 ]; then
    python bots/mainstream_fallback_supply_v1.py || true
    consecutive_no_new=0
  fi

  sleep 900
done
