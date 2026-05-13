#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
THRESHOLD = float(os.environ.get("TREND_PROPOSAL_THRESHOLD", "60"))
LIMIT = int(os.environ.get("TREND_PROPOSAL_LIMIT", "5"))
DRY_RUN_DIGEST = os.environ.get("TREND_PROPOSAL_DRY_RUN_DIGEST", "1") != "0"
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
        "trend_items": {"id", "source", "github_url", "repo_full_name", "description", "license_key", "stars", "forks", "pushed_at"},
        "trend_scores": {"item_id", "usefulness_score", "reuse_score", "license_score", "star_velocity_score", "maintenance_score", "safety_score", "noise_penalty", "total_score"},
        "trend_proposals": {"item_id", "proposal_status", "candidate_score", "proposal_title", "proposal_summary", "safety_summary", "next_prompt", "approval_required"},
    }
    for table, cols in required.items():
        present = {r["name"] for r in db.execute(f"pragma table_info({table})").fetchall()}
        missing = sorted(cols - present)
        if missing:
            raise RuntimeError(
                f"schema_missing table={table} cols={','.join(missing)} "
                "apply migrations/20260513_trend_intelligence_v1.sql first"
            )


def compact(text: str, limit: int = 240) -> str:
    return " ".join((text or "").split())[:limit]


def keyword_score(row) -> float:
    text = f"{row['repo_full_name']} {row['description']} {row['language']}".lower()
    hits = sum(1 for word in USEFUL_KEYWORDS if word in text)
    return min(100.0, hits * 18.0)


def reuse_score(row) -> float:
    text = f"{row['description']} {row['language']}".lower()
    score = 25.0
    if "sqlite" in text:
        score += 25
    if "python" in text or str(row["language"]).lower() == "python":
        score += 20
    if "agent" in text or "runtime" in text:
        score += 25
    if "kubernetes" in text or "cloud" in text:
        score -= 10
    return max(0.0, min(100.0, score))


def license_score(license_key: str) -> tuple[float, str]:
    key = (license_key or "").lower()
    if key in SAFE_LICENSES:
        return 100.0, f"license {key} is permissive"
    if key in RISKY_LICENSES:
        return 35.0, f"license {key} requires review"
    if not key or key == "noassertion":
        return 20.0, "license unknown"
    return 55.0, f"license {key} needs manual review"


def star_velocity_score(row) -> float:
    stars = int(row["stars"] or 0)
    forks = int(row["forks"] or 0)
    base = min(70.0, stars / 150.0)
    fork_signal = min(20.0, forks / 50.0)
    recent_signal = 10.0 if row["pushed_at"] else 0.0
    return min(100.0, base + fork_signal + recent_signal)


def maintenance_score(row) -> float:
    return 80.0 if row["pushed_at"] else 30.0


def noise_penalty(row) -> float:
    text = f"{row['repo_full_name']} {row['description']}".lower()
    return 30.0 if any(word in text for word in NOISE_KEYWORDS) else 0.0


def safety_score(row, license_value: float) -> float:
    if license_value < 30:
        return 35.0
    if noise_penalty(row) > 0:
        return 45.0
    return 90.0


def score_item(row) -> dict:
    license_value, license_reason = license_score(row["license_key"])
    values = {
        "usefulness_score": keyword_score(row),
        "reuse_score": reuse_score(row),
        "license_score": license_value,
        "star_velocity_score": star_velocity_score(row),
        "maintenance_score": maintenance_score(row),
        "safety_score": safety_score(row, license_value),
        "noise_penalty": noise_penalty(row),
    }
    total = (
        values["usefulness_score"] * 0.30
        + values["reuse_score"] * 0.25
        + values["license_score"] * 0.10
        + values["star_velocity_score"] * 0.15
        + values["maintenance_score"] * 0.10
        + values["safety_score"] * 0.10
        - values["noise_penalty"]
    )
    values["total_score"] = max(0.0, min(100.0, total))
    values["score_reason"] = (
        f"{license_reason}; stars={int(row['stars'] or 0)} forks={int(row['forks'] or 0)} "
        f"reuse={values['reuse_score']:.1f} useful={values['usefulness_score']:.1f}"
    )
    return values


def upsert_score(db, row, score):
    db.execute("""
        insert into trend_scores
        (
          item_id, usefulness_score, reuse_score, license_score,
          star_velocity_score, maintenance_score, safety_score, noise_penalty,
          total_score, score_reason, scored_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        on conflict(item_id) do update set
          usefulness_score=excluded.usefulness_score,
          reuse_score=excluded.reuse_score,
          license_score=excluded.license_score,
          star_velocity_score=excluded.star_velocity_score,
          maintenance_score=excluded.maintenance_score,
          safety_score=excluded.safety_score,
          noise_penalty=excluded.noise_penalty,
          total_score=excluded.total_score,
          score_reason=excluded.score_reason,
          scored_at=datetime('now')
    """, (
        row["id"],
        score["usefulness_score"],
        score["reuse_score"],
        score["license_score"],
        score["star_velocity_score"],
        score["maintenance_score"],
        score["safety_score"],
        score["noise_penalty"],
        score["total_score"],
        score["score_reason"],
    ))


def proposal_text(row, score) -> tuple[str, str, str, str]:
    title = f"Evaluate OSS reuse: {row['repo_full_name']}"
    summary = (
        f"{row['github_url']} score={score['total_score']:.1f}. "
        f"{compact(row['description'], 180)}"
    )
    safety = (
        "Approval required. Do not install, execute, deploy, commit, or push. "
        f"License={row['license_key'] or 'unknown'}; {score['score_reason']}"
    )
    next_prompt = "\n".join([
        "Review this GitHub OSS trend for OpenClaw reuse.",
        f"GitHub URL: {row['github_url']}",
        f"Repository: {row['repo_full_name']}",
        f"License: {row['license_key'] or 'unknown'}",
        "Do not install or execute external code.",
        "Produce a minimal reuse proposal, safety review, and smoke-test plan only.",
    ])
    return title, summary, safety, next_prompt


def upsert_proposal(db, row, score):
    if score["total_score"] < THRESHOLD or score["safety_score"] < 50:
        return False
    title, summary, safety, next_prompt = proposal_text(row, score)
    db.execute("""
        insert into trend_proposals
        (
          item_id, proposal_status, candidate_score, proposal_title,
          proposal_summary, safety_summary, next_prompt, approval_required,
          created_at, updated_at
        )
        values (?, 'queued', ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
        on conflict(item_id) do update set
          candidate_score=max(trend_proposals.candidate_score, excluded.candidate_score),
          proposal_title=excluded.proposal_title,
          proposal_summary=excluded.proposal_summary,
          safety_summary=excluded.safety_summary,
          next_prompt=excluded.next_prompt,
          approval_required=1,
          updated_at=datetime('now')
        where trend_proposals.proposal_status='queued'
    """, (row["id"], score["total_score"], title, summary, safety, next_prompt))
    return True


def build_digest(db) -> str:
    rows = db.execute("""
        select p.*, i.repo_full_name, i.github_url, i.license_key, s.score_reason
        from trend_proposals p
        join trend_items i on i.id=p.item_id
        join trend_scores s on s.item_id=i.id
        where p.proposal_status='queued'
        order by p.candidate_score desc, p.id asc
        limit ?
    """, (LIMIT,)).fetchall()
    lines = ["OpenClaw trend intelligence digest", f"queued={len(rows)} threshold={THRESHOLD:.1f}", ""]
    for row in rows:
        lines.extend([
            f"- proposal_id={row['id']} score={float(row['candidate_score'] or 0):.1f} repo={row['repo_full_name']}",
            f"  url: {row['github_url']}",
            f"  license: {row['license_key'] or 'unknown'}",
            f"  why: {compact(row['proposal_summary'], 180)}",
            f"  safety: {compact(row['safety_summary'], 180)}",
            "  approval: required before any codex_tasks/router_tasks conversion",
        ])
    return "\n".join(lines).strip()


def run_once() -> tuple[int, int, str]:
    db = connect()
    try:
        ensure_schema(db)
        rows = db.execute("select * from trend_items where source='github' order by id asc").fetchall()
        proposals = 0
        for row in rows:
            score = score_item(row)
            upsert_score(db, row, score)
            if upsert_proposal(db, row, score):
                proposals += 1
        digest = build_digest(db)
        db.commit()
        return len(rows), proposals, digest
    finally:
        db.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Build GitHub-only trend proposals from ingested fake payloads.")
    parser.add_argument("--dry-run-digest", action="store_true", default=DRY_RUN_DIGEST)
    parser.add_argument("--approve", type=int, help="reserved; approval execution is intentionally not implemented")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.approve:
        raise SystemExit("approval execution is not implemented; proposals require a separate human approval flow")
    items, proposals, digest = run_once()
    if args.dry_run_digest:
        print("[trend_proposal_builder_v1] dry_run digest_begin")
        print(digest)
        print("[trend_proposal_builder_v1] dry_run digest_end")
    print(f"[trend_proposal_builder_v1] items={items} proposals={proposals}")


if __name__ == "__main__":
    main()
