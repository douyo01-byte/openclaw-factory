#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory" || exit 1
export DB_PATH="$HOME/AI/openclaw-factory/data/openclaw.db"
python scripts/write_ops_snapshot.py >/dev/null
cat docs/_auto_progress.md >> docs/08_HANDOVER.md
