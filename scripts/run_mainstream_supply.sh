#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/AI/openclaw-factory-daemon" || exit 1
source .venv/bin/activate || exit 1
export PYTHONPATH="$HOME/AI/openclaw-factory-daemon"
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export OCLAW_DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

toggle_file="data/mainstream_supply.mode"
state_file="data/mainstream_supply.bias_state"
mkdir -p data
[ -f "$toggle_file" ] || echo code_review > "$toggle_file"
[ -f "$state_file" ] || echo 0 > "$state_file"

run_one() {
  local out
  out=$(python "$1" 2>&1 || true)
  echo "$out"
}

top_bias_key="$(sqlite3 "$DB_PATH" "
select coalesce(bias_key,'')
from supply_bias
order by weight desc, source_pattern_count desc, id desc
limit 1;
" 2>/dev/null || true)"
top_bias_type="$(sqlite3 "$DB_PATH" "
select coalesce(bias_type,'')
from supply_bias
order by weight desc, source_pattern_count desc, id desc
limit 1;
" 2>/dev/null || true)"
top_bias_weight="$(sqlite3 "$DB_PATH" "
select coalesce(round(weight,2),0)
from supply_bias
order by weight desc, source_pattern_count desc, id desc
limit 1;
" 2>/dev/null || true)"

bias_state="$(cat "$state_file" 2>/dev/null || echo 0)"
mode="$(cat "$toggle_file" 2>/dev/null || echo code_review)"

echo "=== mainstream tick start $(date '+%F %T') ==="
echo "mode_before=$mode"
echo "top_bias_type=${top_bias_type:-}"
echo "top_bias_key=${top_bias_key:-}"
echo "top_bias_weight=${top_bias_weight:-0}"
echo "bias_state_before=$bias_state"

preferred="code_review"

case "${top_bias_key:-}" in
  watcher|db|health|log)
    preferred="fallback"
    ;;
  *)
    preferred="code_review"
    ;;
esac

next_mode="$mode"

if [ "$preferred" = "fallback" ]; then
  case "$bias_state" in
    0|1|2)
      next_mode="fallback"
      ;;
    *)
      next_mode="code_review"
      ;;
  esac
  next_state=$(( (bias_state + 1) % 4 ))
else
  case "$bias_state" in
    0|1|2)
      next_mode="code_review"
      ;;
    *)
      next_mode="fallback"
      ;;
  esac
  next_state=$(( (bias_state + 1) % 4 ))
fi

echo "preferred_mode=$preferred"
echo "mode_selected=$next_mode"

if [ "$next_mode" = "code_review" ]; then
  run_one bots/code_review_engine_v1.py
else
  python bots/mainstream_fallback_supply_v1.py || true
fi

echo "$next_mode" > "$toggle_file"
echo "$next_state" > "$state_file"

active=$(sqlite3 "$DB_PATH" "
select count(*)
from dev_proposals
where status='approved'
  and coalesce(project_decision,'')='execute_now'
  and coalesce(guard_status,'')='safe';
" 2>/dev/null || echo 0)

echo "active_execute_now_safe=$active"
echo "mode_after=$(cat "$toggle_file" 2>/dev/null || echo NO_MODE)"
echo "bias_state_after=$(cat "$state_file" 2>/dev/null || echo NO_STATE)"
echo "=== mainstream tick end $(date '+%F %T') ==="
