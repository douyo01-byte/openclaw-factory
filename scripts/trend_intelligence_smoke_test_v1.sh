#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/trend_intelligence.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT
DB="$WORKDIR/trend.sqlite3"
PAYLOAD="$WORKDIR/fake_github.json"
OUT1="$WORKDIR/ingest.out"
OUT2="$WORKDIR/proposal.out"

export DB_PATH="$DB"
export TREND_PROPOSAL_THRESHOLD=55
export TREND_PROPOSAL_LIMIT=5
export TREND_PROPOSAL_DRY_RUN_DIGEST=1

echo "[trend_intelligence_smoke] checking files"
test -f migrations/20260513_trend_intelligence_v1.sql
test -f bots/trend_intelligence_v1.py
test -f bots/trend_proposal_builder_v1.py

echo "[trend_intelligence_smoke] checking static safety guards"
if rg -n "urllib|requests|subprocess|os\\.system|git (clone|commit|push)|launchctl|npm install|pip install" \
  bots/trend_intelligence_v1.py bots/trend_proposal_builder_v1.py; then
  echo "unsafe network/install/execute automation found" >&2
  exit 1
fi
rg -n "apply migrations/20260513_trend_intelligence_v1.sql first" \
  bots/trend_intelligence_v1.py bots/trend_proposal_builder_v1.py >/dev/null

echo "[trend_intelligence_smoke] checking syntax"
"$PYTHON" -m py_compile bots/trend_intelligence_v1.py bots/trend_proposal_builder_v1.py
bash -n scripts/trend_intelligence_smoke_test_v1.sh

echo "[trend_intelligence_smoke] applying migration on temp DB"
sqlite3 "$DB" < migrations/20260513_trend_intelligence_v1.sql

cat > "$PAYLOAD" <<'JSON'
{
  "items": [
    {
      "id": 101,
      "full_name": "example/agent-runtime-sandbox",
      "html_url": "https://github.com/example/agent-runtime-sandbox",
      "description": "Python agent runtime sandbox with sqlite workflow orchestration and tool observability",
      "language": "Python",
      "license": {"spdx_id": "MIT"},
      "stargazers_count": 18400,
      "forks_count": 1200,
      "open_issues_count": 12,
      "pushed_at": "2026-05-12T00:00:00Z",
      "created_at": "2025-10-01T00:00:00Z"
    },
    {
      "id": 102,
      "full_name": "example/agent-runtime-sandbox",
      "html_url": "https://github.com/example/agent-runtime-sandbox",
      "description": "Duplicate should update the same trend item",
      "language": "Python",
      "license": {"spdx_id": "MIT"},
      "stargazers_count": 18500,
      "forks_count": 1250,
      "open_issues_count": 10,
      "pushed_at": "2026-05-13T00:00:00Z",
      "created_at": "2025-10-01T00:00:00Z"
    },
    {
      "id": 103,
      "full_name": "example/crypto-airdrop-bot",
      "html_url": "https://github.com/example/crypto-airdrop-bot",
      "description": "crypto airdrop giveaway automation",
      "language": "JavaScript",
      "license": null,
      "stargazers_count": 90000,
      "forks_count": 5000,
      "open_issues_count": 200,
      "pushed_at": "",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
JSON

echo "[trend_intelligence_smoke] ingesting fake GitHub payload"
"$PYTHON" bots/trend_intelligence_v1.py --payload "$PAYLOAD" > "$OUT1"
cat "$OUT1"
rg -n "ingested github_items=3" "$OUT1" >/dev/null

echo "[trend_intelligence_smoke] building dry-run proposals"
"$PYTHON" bots/trend_proposal_builder_v1.py --dry-run-digest > "$OUT2"
cat "$OUT2"

echo "[trend_intelligence_smoke] validating DB state"
"$PYTHON" - <<'PY'
import os
import sqlite3

db = sqlite3.connect(os.environ["DB_PATH"])
db.row_factory = sqlite3.Row
items = db.execute("select count(*) as n from trend_items").fetchone()["n"]
scores = db.execute("select count(*) as n from trend_scores").fetchone()["n"]
proposals = db.execute("select count(*) as n from trend_proposals").fetchone()["n"]
assert items == 2, items
assert scores == 2, scores
assert proposals == 1, proposals
row = db.execute("""
    select p.*, i.github_url, i.license_key
    from trend_proposals p
    join trend_items i on i.id=p.item_id
""").fetchone()
assert row["proposal_status"] == "queued", row["proposal_status"]
assert row["approval_required"] == 1, row["approval_required"]
assert row["github_url"] == "https://github.com/example/agent-runtime-sandbox", row["github_url"]
assert row["license_key"] == "mit", row["license_key"]
db.close()
PY

rg -n "OpenClaw trend intelligence digest" "$OUT2" >/dev/null
rg -n "https://github.com/example/agent-runtime-sandbox" "$OUT2" >/dev/null
rg -n "approval" "$OUT2" >/dev/null
if rg -n "crypto-airdrop-bot" "$OUT2"; then
  echo "noisy low-safety item should not be proposed" >&2
  exit 1
fi

echo "[trend_intelligence_smoke] complete"
