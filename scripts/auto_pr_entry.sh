#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "$HOME/AI/openclaw-factory"
source .venv/bin/activate

export PYTHONPATH="$PWD"
export DB_PATH="$PWD/data/openclaw.db"
export OCLAW_DB_PATH="$PWD/data/openclaw.db"
export GITHUB_REPO="douyo01-byte/openclaw-factory"

# 1) Prefer launchctl-provided token (works for LaunchAgents)
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  if command -v launchctl >/dev/null 2>&1; then
    t="$(launchctl getenv GITHUB_TOKEN 2>/dev/null || true)"
    if [[ -n "$t" ]]; then export GITHUB_TOKEN="$t"; fi
  fi
fi

# 2) Fallback to gh auth token (works for interactive)
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  if command -v gh >/dev/null 2>&1; then
    export GITHUB_TOKEN="$(gh auth token)"
  fi
fi

# Debug (will go to auto_pr.out when launched via launchd)
python - <<'PY'
import os
print("GITHUB_REPO=", os.environ.get("GITHUB_REPO"))
print("TOKEN_SET=", bool(os.environ.get("GITHUB_TOKEN")))
print("DB=", os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH"))
PY

exec python -u -m bots.dev_pr_creator_v1
