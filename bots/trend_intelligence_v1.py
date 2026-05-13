#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAYLOAD = ROOT / "tmp_exec/fake_github_trends.json"
SAFE_LICENSES = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "mpl-2.0"}
RISKY_LICENSES = {"gpl-2.0", "gpl-3.0", "agpl-3.0", "lgpl-2.1", "lgpl-3.0"}
USEFUL_KEYWORDS = {
    "agent", "agents", "runtime", "workflow", "automation", "sqlite",
    "eval", "sandbox", "orchestration", "observability", "tool",
}
NOISE_KEYWORDS = {"crypto", "airdrop", "casino", "giveaway", "nsfw"}


def connect():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("pragma busy_timeout=30000")
    return db


def ensure_schema(db):
    required = {
        "trend_items": {"source", "url", "github_url", "repo_full_name", "license_key", "stars", "raw_json"},
        "trend_scores": {"item_id", "license_score", "star_velocity_score", "total_score", "score_reason"},
        "trend_proposals": {"item_id", "proposal_status", "candidate_score", "approval_required", "next_prompt"},
    }
    for table, cols in required.items():
        present = {r["name"] for r in db.execute(f"pragma table_info({table})").fetchall()}
        missing = sorted(cols - present)
        if missing:
            raise RuntimeError(
                f"schema_missing table={table} cols={','.join(missing)} "
                "apply migrations/20260513_trend_intelligence_v1.sql first"
            )


def as_items(payload):
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, list):
        return payload
    raise ValueError("fake GitHub payload must be a list or an object with items")


def license_key(repo: dict) -> str:
    license_value = repo.get("license")
    if isinstance(license_value, dict):
        return str(license_value.get("spdx_id") or license_value.get("key") or "").lower()
    return str(license_value or "").lower()


def repo_url(repo: dict) -> str:
    return str(repo.get("html_url") or repo.get("url") or "").strip()


def repo_name(repo: dict) -> str:
    return str(repo.get("full_name") or repo.get("name") or "").strip()


def upsert_item(db, repo: dict) -> int:
    full_name = repo_name(repo)
    url = repo_url(repo)
    if not url.startswith("https://github.com/") or not full_name:
        raise ValueError(f"invalid GitHub repo payload: full_name={full_name!r} url={url!r}")
    owner = full_name.split("/", 1)[0] if "/" in full_name else ""
    db.execute("""
        insert into trend_items
        (
          source, external_id, title, url, github_url, repo_full_name, owner,
          description, language, license_key, stars, forks, open_issues,
          pushed_at, created_at_source, raw_json, safety_status, first_seen_at, last_seen_at
        )
        values
        ('github', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))
        on conflict(source, url) do update set
          external_id=excluded.external_id,
          title=excluded.title,
          github_url=excluded.github_url,
          repo_full_name=excluded.repo_full_name,
          owner=excluded.owner,
          description=excluded.description,
          language=excluded.language,
          license_key=excluded.license_key,
          stars=excluded.stars,
          forks=excluded.forks,
          open_issues=excluded.open_issues,
          pushed_at=excluded.pushed_at,
          created_at_source=excluded.created_at_source,
          raw_json=excluded.raw_json,
          last_seen_at=datetime('now')
    """, (
        str(repo.get("id") or full_name),
        full_name,
        url,
        url,
        full_name,
        owner,
        str(repo.get("description") or ""),
        str(repo.get("language") or ""),
        license_key(repo),
        int(repo.get("stargazers_count") or repo.get("stars") or 0),
        int(repo.get("forks_count") or repo.get("forks") or 0),
        int(repo.get("open_issues_count") or 0),
        str(repo.get("pushed_at") or ""),
        str(repo.get("created_at") or ""),
        json.dumps(repo, ensure_ascii=False, sort_keys=True),
    ))
    row = db.execute("select id from trend_items where source='github' and url=?", (url,)).fetchone()
    return int(row["id"])


def ingest_payload(path: Path) -> int:
    db = connect()
    try:
        ensure_schema(db)
        payload = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for repo in as_items(payload):
            upsert_item(db, repo)
            count += 1
        db.commit()
        return count
    finally:
        db.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest fake GitHub trend payloads only.")
    parser.add_argument("--payload", default=str(DEFAULT_PAYLOAD), help="local fake GitHub JSON payload")
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.payload)
    if not path.is_file():
        raise SystemExit(f"payload not found: {path}")
    count = ingest_payload(path)
    print(f"[trend_intelligence_v1] ingested github_items={count} payload={path}")


if __name__ == "__main__":
    main()
