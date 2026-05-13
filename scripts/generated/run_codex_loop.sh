#!/usr/bin/env bash
set -euo pipefail

cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
export CODEX_LOOP_DRY_RUN="${CODEX_LOOP_DRY_RUN:-1}"
export CODEX_LOOP_MAX_TASKS="${CODEX_LOOP_MAX_TASKS:-1}"

python3 bots/codex_task_bridge_v1.py
