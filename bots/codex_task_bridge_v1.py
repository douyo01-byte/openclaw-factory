#!/usr/bin/env python3
import os
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
DRY_RUN_DEFAULT = os.environ.get("CODEX_LOOP_DRY_RUN", "1") != "0"
MAX_TASKS = int(os.environ.get("CODEX_LOOP_MAX_TASKS", "1"))
DEFAULT_TIMEOUT = int(os.environ.get("CODEX_TASK_TIMEOUT_SECONDS", "1800"))
BRAIN_PATH = ROOT / "docs/OPENCLAW_BRAIN.md"

VALID_STATUSES = {"new", "running", "blocked", "review", "done"}

PROMPT_TEMPLATE = """[CODEX_AUTONOMOUS_TASK]
Read docs/OPENCLAW_BRAIN.md before acting.

Operating rules:
- Keep the diff minimal.
- Treat runtime logs, database state, and actual command output as truth.
- Run the narrowest meaningful smoke test before reporting completion.
- Do not commit or push from this loop.
- If blocked, save the blocker clearly.

Task:
- id: {task_id}
- title: {title}
- dry_run: {dry_run}

Details:
{task_text}

OpenClaw brain excerpt:
{brain}
"""


def connect():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("pragma busy_timeout=30000")
    return db


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
        create table if not exists codex_task_runs (
          id integer primary key autoincrement,
          task_id integer not null,
          status text not null default 'running',
          dry_run integer not null default 1,
          prompt_text text not null default '',
          result_summary text not null default '',
          error_text text not null default '',
          started_at text not null default (datetime('now')),
          finished_at text not null default '',
          elapsed_seconds real not null default 0,
          foreign key(task_id) references codex_tasks(id)
        )
    """)


def read_brain() -> str:
    if not BRAIN_PATH.exists():
        return "docs/OPENCLAW_BRAIN.md is missing. Continue with local runtime truth and minimal diff."
    text = BRAIN_PATH.read_text(encoding="utf-8", errors="replace").strip()
    return text[:4000]


def build_prompt(task) -> str:
    return PROMPT_TEMPLATE.format(
        task_id=task["id"],
        title=task["title"] or "(untitled)",
        dry_run=int(task["dry_run"] or 0),
        task_text=task["task_text"],
        brain=read_brain(),
    )


def block_timed_out(db):
    now = time.time()
    rows = db.execute("""
        select id, timeout_seconds, updated_at
        from codex_tasks
        where status='running'
    """).fetchall()
    for row in rows:
        updated = db.execute("select strftime('%s', ?) as ts", (row["updated_at"],)).fetchone()["ts"]
        updated_ts = float(updated or 0)
        timeout = int(row["timeout_seconds"] or DEFAULT_TIMEOUT)
        if updated_ts and now - updated_ts > timeout:
            summary = f"blocked: task exceeded timeout_seconds={timeout}"
            db.execute("""
                update codex_tasks
                set status='blocked',
                    result_summary=?,
                    updated_at=datetime('now')
                where id=?
            """, (summary, row["id"]))
            db.execute("""
                update codex_task_runs
                set status='blocked',
                    error_text=?,
                    finished_at=datetime('now'),
                    elapsed_seconds=max(0, strftime('%s','now') - strftime('%s', started_at))
                where task_id=?
                  and status='running'
            """, (summary, row["id"]))


def claim_task(db):
    row = db.execute("""
        select *
        from codex_tasks
        where status='new'
        order by priority desc, id asc
        limit 1
    """).fetchone()
    if not row:
        return None
    db.execute("""
        update codex_tasks
        set status='running',
            updated_at=datetime('now')
        where id=?
          and status='new'
    """, (row["id"],))
    if db.total_changes <= 0:
        return None
    return db.execute("select * from codex_tasks where id=?", (row["id"],)).fetchone()


def save_run_start(db, task, prompt: str) -> int:
    cur = db.execute("""
        insert into codex_task_runs
        (task_id, status, dry_run, prompt_text, started_at)
        values
        (?, 'running', ?, ?, datetime('now'))
    """, (task["id"], int(task["dry_run"] or 0), prompt))
    db.execute("""
        update codex_tasks
        set prompt_text=?,
            updated_at=datetime('now')
        where id=?
    """, (prompt, task["id"]))
    return int(cur.lastrowid)


def finish_run(db, task_id: int, run_id: int, status: str, summary: str, error: str = ""):
    if status not in VALID_STATUSES:
        status = "blocked"
    db.execute("""
        update codex_task_runs
        set status=?,
            result_summary=?,
            error_text=?,
            finished_at=datetime('now'),
            elapsed_seconds=max(0, strftime('%s','now') - strftime('%s', started_at))
        where id=?
    """, (status, summary, error, run_id))
    db.execute("""
        update codex_tasks
        set status=?,
            result_summary=?,
            updated_at=datetime('now')
        where id=?
    """, (status, summary, task_id))


def run_task(db, task):
    prompt = build_prompt(task)
    run_id = save_run_start(db, task, prompt)
    if int(task["dry_run"] if task["dry_run"] is not None else int(DRY_RUN_DEFAULT)):
        summary = "DRY_RUN: codex prompt prepared and saved; no files changed; no commit or push."
        finish_run(db, task["id"], run_id, "review", summary)
        return summary
    summary = "blocked: live Codex execution is intentionally disabled; use dry-run result for human review."
    finish_run(db, task["id"], run_id, "blocked", summary, summary)
    return summary


def run_once():
    with connect() as db:
        ensure_schema(db)
        block_timed_out(db)
        processed = 0
        for _ in range(MAX_TASKS):
            task = claim_task(db)
            if not task:
                break
            run_task(db, task)
            processed += 1
        db.commit()
    print(f"[codex_task_bridge_v1] processed={processed}", flush=True)


if __name__ == "__main__":
    run_once()
