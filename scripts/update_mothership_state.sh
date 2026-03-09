#!/usr/bin/env bash
set -euo pipefail

cd ~/AI/openclaw-factory || exit 1

DB=../openclaw-factory-daemon/data/openclaw.db

approved=$(sqlite3 "$DB" "select count(*) from dev_proposals where status='approved';")
merged=$(sqlite3 "$DB" "select count(*) from dev_proposals where status='merged';")
open=$(sqlite3 "$DB" "select count(*) from dev_proposals where dev_stage='pr_created';")

cat > docs/06_CURRENT_STATE.md <<EOF
# OpenClaw Current State

approved: $approved
merged: $merged
pr_created: $open

updated: $(date)
EOF
