#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
MAX_RUNS = int(os.environ.get("CODEX_REVIEW_LOOP_MAX_RUNS", "5"))
SUMMARY_LIMIT = int(os.environ.get("CODEX_REVIEW_SUMMARY_LIMIT", "1200"))


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
          elapsed_seconds real not null default 0
        )
    """)
    db.execute("""
        create table if not exists codex_run_transcripts (
          id integer primary key autoincrement,
          task_id integer not null default 0,
          run_id integer not null,
          transcript_text text not null default '',
          result_summary text not null default '',
          diff_summary text not null default '',
          test_summary text not null default '',
          risk_summary text not null default '',
          created_at text not null default (datetime('now')),
          unique(run_id)
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
    db.execute("""
        create index if not exists idx_codex_review_queue_status
        on codex_review_queue(review_status, candidate_score, id)
    """)


def compact(text: str, limit: int = SUMMARY_LIMIT) -> str:
    one_line = " ".join((text or "").split())
    return one_line[:limit]


def classify_tests(text: str) -> str:
    lower = (text or "").lower()
    hits = []
    for token in ["py_compile", "smoke", "bash -n", "pytest", "node --check"]:
        if token in lower:
            hits.append(token)
    return ", ".join(hits) if hits else "not mentioned"


def classify_risk(row) -> str:
    status = row["status"]
    text = f"{row['result_summary']}\n{row['error_text']}".lower()
    if status == "blocked":
        return "blocked run requires human direction"
    if "error" in text or "failed" in text or "blocked" in text:
        return "residual risk mentioned in result"
    return "no explicit residual risk found"


def build_review_summary(row, task) -> str:
    title = task["title"] if task else ""
    task_text = task["task_text"] if task else ""
    body = row["result_summary"] or row["error_text"] or ""
    return "\n".join([
        "[CODEX_REVIEW_SUMMARY]",
        f"task_id: {row['task_id']}",
        f"run_id: {row['id']}",
        f"status: {row['status']}",
        f"title: {compact(title, 160)}",
        f"task: {compact(task_text, 320)}",
        f"result: {compact(body)}",
        f"tests: {classify_tests(body)}",
        f"risk: {classify_risk(row)}",
    ])


def build_next_prompt(row, task, review_summary: str) -> str:
    title = task["title"] if task else f"Codex follow-up for run {row['id']}"
    task_text = task["task_text"] if task else ""
    return "\n".join([
        "[CODEX_REVIEW_FOLLOWUP]",
        "Read docs/OPENCLAW_BRAIN.md before acting.",
        "Use minimal diff only.",
        "Use runtime logs, database state, and command output as truth.",
        "Run the narrowest meaningful smoke test before reporting completion.",
        "Do not commit or push from this loop.",
        "",
        f"Source task id: {row['task_id']}",
        f"Source run id: {row['id']}",
        f"Source title: {compact(title, 160)}",
        "",
        "Original task:",
        compact(task_text, 1200),
        "",
        "Review summary:",
        review_summary,
        "",
        "Next action:",
        "Address only the concrete blocker or residual risk above. If there is no blocker, verify and report current status.",
    ])


def candidate_score(row, task) -> float:
    score = float(task["priority"] if task else 0)
    if row["status"] == "blocked":
        score += 20
    elif row["status"] == "review":
        score += 10
    if row["error_text"]:
        score += 5
    return score


def fetch_runs(db):
    return db.execute("""
        select r.*
        from codex_task_runs r
        left join codex_review_queue q on q.source_run_id=r.id
        where r.status in ('review', 'blocked')
          and q.id is null
        order by r.id asc
        limit ?
    """, (MAX_RUNS,)).fetchall()


def process_run(db, row) -> bool:
    task = db.execute("select * from codex_tasks where id=?", (row["task_id"],)).fetchone()
    transcript = row["prompt_text"] or ""
    result = row["result_summary"] or row["error_text"] or ""
    review_summary = build_review_summary(row, task)
    next_prompt = build_next_prompt(row, task, review_summary)
    db.execute("""
        insert or ignore into codex_run_transcripts
        (task_id, run_id, transcript_text, result_summary, test_summary, risk_summary, created_at)
        values
        (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        row["task_id"],
        row["id"],
        transcript,
        result,
        classify_tests(result),
        classify_risk(row),
    ))
    cur = db.execute("""
        insert or ignore into codex_review_queue
        (source_task_id, source_run_id, review_status, candidate_score, review_summary, next_prompt, created_at, updated_at)
        values
        (?, ?, 'queued', ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        row["task_id"],
        row["id"],
        candidate_score(row, task),
        review_summary,
        next_prompt,
    ))
    return cur.rowcount > 0


def run_once() -> int:
    db = connect()
    try:
        ensure_schema(db)
        processed = 0
        for row in fetch_runs(db):
            if process_run(db, row):
                processed += 1
        db.commit()
        return processed
    finally:
        db.close()


def main():
    processed = run_once()
    print(f"[codex_review_loop_v1] queued={processed}", flush=True)


if __name__ == "__main__":
    main()

