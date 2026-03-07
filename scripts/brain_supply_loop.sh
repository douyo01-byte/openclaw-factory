#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
mkdir -p logs
run_if_exists() {
  local f="$1"
  if [ -f "$f" ]; then
    python -u "$f" >> logs/brain_supply.out 2>> logs/brain_supply.err || true
    return 0
  fi
  return 1
}
while true
do
  ran=0
  run_if_exists bots/market_brain_v1.py && ran=1 || true
  run_if_exists bots/business_brain_v1.py && ran=1 || true
  run_if_exists bots/revenue_brain_v1.py && ran=1 || true
  run_if_exists bots/self_improve_v1.py && ran=1 || true
  run_if_exists bots/dev_proposal_generator_v1.py && ran=1 || true
  if [ "$ran" = "0" ]; then
    echo "[brain_supply_loop] no supplier found $(date '+%F %T')" >> logs/brain_supply.err
  fi
  sleep 120
done
