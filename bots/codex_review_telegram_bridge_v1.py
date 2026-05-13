#!/usr/bin/env python3
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
THRESHOLD = float(os.environ.get("CODEX_REVIEW_TG_THRESHOLD", "10"))
LIMIT = int(os.environ.get("CODEX_REVIEW_TG_LIMIT", "3"))
DRY_RUN = os.environ.get("CODEX_REVIEW_TG_DRY_RUN", "1") != "0"
SUMMARY_LIMIT = int(os.environ.get("CODEX_REVIEW_TG_SUMMARY_LIMIT", "700"))


def connect():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("pragma busy_timeout=30000")
    return db


def ensure_schema(db):
    db.execute("""
        create table if not exists codex_review_telegram_notifications (
          id integer primary key autoincrement,
          queue_id integer not null,
          source_task_id integer not null default 0,
          source_run_id integer not null default 0,
          candidate_score real not null default 0,
          message_id text not null default '',
          sent_at text not null default (datetime('now')),
          unique(queue_id)
        )
    """)
    db.execute("""
        create index if not exists idx_codex_review_telegram_notifications_sent
        on codex_review_telegram_notifications(sent_at, queue_id)
    """)


def compact(text: str, limit: int = SUMMARY_LIMIT) -> str:
    return "\n".join(line.rstrip() for line in (text or "").strip().splitlines())[:limit]


def extract_risk(review_summary: str) -> str:
    for line in (review_summary or "").splitlines():
        if line.lower().startswith("risk:"):
            return line.split(":", 1)[1].strip() or "not specified"
    lower = (review_summary or "").lower()
    match = re.search(r"residual risk[: ]+([^\n]+)", lower)
    if match:
        return match.group(1).strip()
    return "not specified"


def fetch_candidates(db):
    return db.execute("""
        select q.*
        from codex_review_queue q
        left join codex_review_telegram_notifications n on n.queue_id=q.id
        where q.review_status='queued'
          and q.candidate_score >= ?
          and n.id is null
        order by q.candidate_score desc, q.id asc
        limit ?
    """, (THRESHOLD, LIMIT)).fetchall()


def build_message(row) -> str:
    summary = compact(row["review_summary"])
    risk = extract_risk(row["review_summary"])
    return "\n".join([
        "Codex review queued",
        "",
        f"queue_id: {row['id']}",
        f"task_id: {row['source_task_id']}",
        f"score: {row['candidate_score']:.1f}",
        "",
        "summary:",
        summary or "(empty)",
        "",
        "residual risk:",
        risk,
        "",
        "approve:",
        f"python3 bots/codex_review_approval_v1.py approve {row['id']}",
        "",
        "reject:",
        f"python3 bots/codex_review_approval_v1.py reject {row['id']} \"reason\"",
    ])


def send_message(text: str) -> str:
    from oclibs.telegram import send as tg_send

    resp = tg_send(text)
    if resp is None:
        raise RuntimeError("telegram send returned None")
    try:
        data = resp.json()
        return str(data.get("result", {}).get("message_id", "") or "")
    except Exception:
        return ""


def record_sent(db, row, message_id: str):
    db.execute("""
        insert into codex_review_telegram_notifications
        (queue_id, source_task_id, source_run_id, candidate_score, message_id, sent_at)
        values (?, ?, ?, ?, ?, datetime('now'))
    """, (
        row["id"],
        row["source_task_id"],
        row["source_run_id"],
        row["candidate_score"],
        message_id,
    ))


def run_once() -> tuple[int, int]:
    db = connect()
    try:
        ensure_schema(db)
        rows = fetch_candidates(db)
        sent = 0
        for row in rows:
            msg = build_message(row)
            if DRY_RUN:
                print("[codex_review_telegram_bridge_v1] dry_run message_begin")
                print(msg)
                print("[codex_review_telegram_bridge_v1] dry_run message_end")
                continue
            message_id = send_message(msg)
            record_sent(db, row, message_id)
            sent += 1
        db.commit()
        return len(rows), sent
    finally:
        db.close()


def main():
    candidates, sent = run_once()
    mode = "dry_run" if DRY_RUN else "send"
    print(
        f"[codex_review_telegram_bridge_v1] mode={mode} candidates={candidates} sent={sent}",
        flush=True,
    )


if __name__ == "__main__":
    main()
