#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.." || exit 1

export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
export OPENAI_MODEL="${OPENAI_MODEL:-gpt-5}"
export KAIKUN04_ORCHESTRATOR_BACKEND="${KAIKUN04_ORCHESTRATOR_BACKEND:-heuristic}"

TASK_TEXT="${1:-Kaikun04 Orchestrator v1 の最小実装を作り、自然文依頼を構造化 JSON 計画に変換したい}"
MODE="${2:-THINK}"
TARGET_SYSTEM="${3:-kaikun04_orchestrator}"
CONTEXT_JSON="${4:-{\"source\":\"manual\",\"goal\":\"skeleton\"}}"

python3 bots/kaikun04_orchestrator_v1.py \
  --task-text "$TASK_TEXT" \
  --mode "$MODE" \
  --target-system "$TARGET_SYSTEM" \
  --context-json "$CONTEXT_JSON" \
  --save-db \
  --pretty
