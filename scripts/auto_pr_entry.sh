#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

cd "$HOME/AI/openclaw-factory"
source .venv/bin/activate

export PYTHONPATH="$PWD"
export DB_PATH="$PWD/data/openclaw.db"
export OCLAW_DB_PATH="$PWD/data/openclaw.db"

export GITHUB_REPO="douyo01-byte/openclaw-factory"
: "${GITHUB_TOKEN:?}"

set -a
source env/telegram.env
set +a

python - <<'PY'
import os
print("GITHUB_REPO=",os.environ.get("GITHUB_REPO"))
print("TOKEN_SET=",bool(os.environ.get("GITHUB_TOKEN")))
print("DB=",os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH"))
PY

exec python -u -m bots.dev_pr_creator_v1
