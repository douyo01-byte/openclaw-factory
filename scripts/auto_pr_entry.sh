#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory"
source .venv/bin/activate
export PYTHONPATH="$PWD"
export DB_PATH="$PWD/data/openclaw.db"
export OCLAW_DB_PATH="$PWD/data/openclaw.db"
export GITHUB_REPO="douyo01-byte/openclaw-factory"
export GITHUB_TOKEN="$(gh auth token)"
set -a
source env/telegram.env
set +a
python - <<'PY'
import os, sqlite3
p=os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH")
print("OCLAW_DB_PATH=",os.environ.get("OCLAW_DB_PATH"))
print("DB_PATH=",os.environ.get("DB_PATH"))
c=sqlite3.connect(p)
print("database_list=",c.execute("pragma database_list").fetchall())
print("has_dev_proposals=",bool(c.execute("select 1 from sqlite_master where type='table' and name='dev_proposals'").fetchone()))
PY
exec python -u -m bots.dev_pr_creator_v1
