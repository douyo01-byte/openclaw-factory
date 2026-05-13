#!/usr/bin/env python3
import argparse
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("CODEX_REVIEW_APPROVAL_TIMEOUT_SECONDS", "1800"))


def connect():
    db = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("pragma busy_timeout=30000")
    return db


def table_columns(db, table: str) -> set[str]:
    return {row["name"] for row in db.execute(f"pragma table_info({table})").fetchall()}


def ensure_schema(db):
    db.execute("""
        create table if not exists codex_tasks (
          id integer primary key autoincrement,
          title text not null default '',
          task_text text not null,
          status text not null default 'new',
          priority integer not null default 0,
          dry_run integer not null default 1,
          timeout_seconds integer not null default 1800,
          prompt_text text not null default '',
          result_summary text not null default '',
          created_at text not null default (datetime('now')),
          updated_at text not null default (datetime('now'))
        )
    """)
    db.execute("""
        create table if not exists codex_review_queue (
          id integer primary key autoincrement,
          source_task_id integer not null default 0,
          source_run_id integer not null default 0,
          review_status text not null default 'queued',
          candidate_score real not null default 0,
          review_summary text not null default '',
          next_prompt text not null default '',
          approval_note text not null default '',
          created_at text not null default (datetime('now')),
          updated_at text not null default (datetime('now')),
          unique(source_run_id)
        )
    """)
    if "created_codex_task_id" not in table_columns(db, "codex_review_queue"):
        raise RuntimeError(
            "codex_review_queue.created_codex_task_id missing; "
            "apply migrations/20260513_codex_review_approval_v1.sql first"
        )
    db.execute("""
        create index if not exists idx_codex_review_queue_approval
        on codex_review_queue(review_status, created_codex_task_id, id)
    """)


def compact(text: str, limit: int = 160) -> str:
    return " ".join((text or "").split())[:limit]


def append_note(existing: str, note: str) -> str:
    note = (note or "").strip()
    if not note:
        return existing or ""
    if not existing:
        return note
    return f"{existing}\n{note}"


def priority_from_score(score) -> int:
    try:
        return max(0, min(100, int(round(float(score)))))
    except Exception:
        return 0


def approve(db, queue_id: int, note: str) -> int:
    db.execute("begin immediate")
    try:
        row = db.execute("select * from codex_review_queue where id=?", (queue_id,)).fetchone()
        if not row:
            raise RuntimeError(f"queue_id not found: {queue_id}")
        if row["review_status"] != "queued":
            raise RuntimeError(f"queue_id {queue_id} is not queued: {row['review_status']}")
        if int(row["created_codex_task_id"] or 0) != 0:
            raise RuntimeError(f"queue_id {queue_id} already created codex_task {row['created_codex_task_id']}")
        next_prompt = (row["next_prompt"] or "").strip()
        if not next_prompt:
            raise RuntimeError(f"queue_id {queue_id} has empty next_prompt")

        title = f"[codex-review] follow-up for queue #{queue_id}"
        result_summary = (
            f"created from codex_review_queue id={queue_id}; "
            f"source_task_id={row['source_task_id']}; source_run_id={row['source_run_id']}"
        )
        cur = db.execute("""
            insert into codex_tasks
            (title, task_text, status, priority, dry_run, timeout_seconds, prompt_text, result_summary, created_at, updated_at)
            values
            (?, ?, 'new', ?, 1, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            title,
            next_prompt,
            priority_from_score(row["candidate_score"]),
            DEFAULT_TIMEOUT_SECONDS,
            next_prompt,
            result_summary,
        ))
        task_id = int(cur.lastrowid)
        approval_note = append_note(
            row["approval_note"],
            f"approved: created_codex_task_id={task_id}; note={compact(note, 300)}",
        )
        updated = db.execute("""
            update codex_review_queue
            set review_status='approved',
                created_codex_task_id=?,
                approval_note=?,
                updated_at=datetime('now')
            where id=?
              and review_status='queued'
              and created_codex_task_id=0
        """, (task_id, approval_note, queue_id))
        if updated.rowcount != 1:
            raise RuntimeError(f"duplicate approval guard blocked queue_id {queue_id}")
        db.execute("commit")
        return task_id
    except Exception:
        db.execute("rollback")
        raise


def reject(db, queue_id: int, note: str) -> None:
    db.execute("begin immediate")
    try:
        row = db.execute("select * from codex_review_queue where id=?", (queue_id,)).fetchone()
        if not row:
            raise RuntimeError(f"queue_id not found: {queue_id}")
        if row["review_status"] != "queued":
            raise RuntimeError(f"queue_id {queue_id} is not queued: {row['review_status']}")
        if int(row["created_codex_task_id"] or 0) != 0:
            raise RuntimeError(f"queue_id {queue_id} already created codex_task {row['created_codex_task_id']}")
        approval_note = append_note(row["approval_note"], f"rejected: note={compact(note, 300)}")
        updated = db.execute("""
            update codex_review_queue
            set review_status='rejected',
                approval_note=?,
                updated_at=datetime('now')
            where id=?
              and review_status='queued'
              and created_codex_task_id=0
        """, (approval_note, queue_id))
        if updated.rowcount != 1:
            raise RuntimeError(f"duplicate reject guard blocked queue_id {queue_id}")
        db.execute("commit")
    except Exception:
        db.execute("rollback")
        raise


def parse_args():
    parser = argparse.ArgumentParser(description="Approve or reject a queued Codex review item.")
    parser.add_argument("action", choices=("approve", "reject"))
    parser.add_argument("queue_id", type=int)
    parser.add_argument("note", nargs="*", help="Optional human note")
    return parser.parse_args()


def main():
    args = parse_args()
    note = " ".join(args.note).strip()
    db = connect()
    try:
        ensure_schema(db)
        if args.action == "approve":
            task_id = approve(db, args.queue_id, note)
            print(f"[codex_review_approval_v1] approved queue_id={args.queue_id} created_codex_task_id={task_id}")
        else:
            reject(db, args.queue_id, note)
            print(f"[codex_review_approval_v1] rejected queue_id={args.queue_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
