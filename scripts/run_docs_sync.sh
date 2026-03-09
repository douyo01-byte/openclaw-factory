#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
export DB_PATH="${DB_PATH:-$HOME/AI/openclaw-factory-daemon/data/openclaw_real.db}"
python3 bots/docs_sync_v1.py
python3 scripts/fix_docs_spacing.py || true
