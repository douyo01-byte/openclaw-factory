#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory/data/openclaw.db}"
exec python3 bots/codex_review_approval_v1.py "$@"
