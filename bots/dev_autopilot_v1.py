#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))

FORBIDDEN_ACTIONS = (
    "Do not launch Codex automatically.",
    "Do not run git add, git commit, git push, or any git write operation.",
    "Do not deploy or publish.",
    "Do not run launchctl or change background services.",
    "Do not send Telegram messages or call notification senders.",
    "Do not purchase, spend money, or trigger external paid actions.",
    "Do not print private access values, private configuration values, or external callback URLs.",
    "Do not delete data or files.",
    "Prefer observation and dry-run commands before any code or DB change.",
)

SENSITIVE_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|passwd|authorization|bearer|webhook|credential|private[_-]?key)"
)


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("pragma busy_timeout=30000")
    return db


def has_table(db: sqlite3.Connection, table: str) -> bool:
    row = db.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_cols(db: sqlite3.Connection, table: str) -> set[str]:
    if not has_table(db, table):
        return set()
    return {r["name"] for r in db.execute(f"pragma table_info({table})").fetchall()}


def clean(text: str | None, limit: int = 1200) -> str:
    value = (text or "").replace("\r", "\n")
    kept = []
    for raw_line in value.splitlines():
        line = raw_line.rstrip()
        if SENSITIVE_RE.search(line):
            kept.append("[redacted sensitive line]")
        else:
            kept.append(line)
    compact = "\n".join(kept).strip()
    return compact[:limit]


def inline(text: str | None, limit: int = 220) -> str:
    return " ".join(clean(text, limit * 2).split())[:limit]


def q1(db: sqlite3.Connection, sql: str, params: Iterable[object] = (), default: int = 0) -> int:
    try:
        row = db.execute(sql, tuple(params)).fetchone()
        return int(row[0] or 0) if row else default
    except sqlite3.Error:
        return default


def count_by_status(db: sqlite3.Connection, table: str, status_col: str) -> str:
    if not has_table(db, table) or status_col not in table_cols(db, table):
        return f"{table}: not configured"
    rows = db.execute(f"""
        select coalesce({status_col}, '') as status, count(*) as n
        from {table}
        group by coalesce({status_col}, '')
        order by status asc
    """).fetchall()
    if not rows:
        return f"{table}: empty"
    return f"{table}: " + " / ".join(f"{r['status'] or '-'}={int(r['n'] or 0)}" for r in rows)


def pick_autopilot_item(db: sqlite3.Connection, queue_id: int = 0) -> sqlite3.Row | None:
    if not has_table(db, "dev_autopilot_queue"):
        return None
    cols = table_cols(db, "dev_autopilot_queue")
    required = {"id", "status", "execution_type", "dry_run", "priority", "task_text"}
    if not required.issubset(cols):
        return None
    optional = {
        "safety_rules": "coalesce(safety_rules, '') as safety_rules",
        "target_files": "coalesce(target_files, '') as target_files",
        "suggested_commands": "coalesce(suggested_commands, '') as suggested_commands",
        "result_summary": "coalesce(result_summary, '') as result_summary",
        "source_table": "coalesce(source_table, '') as source_table",
        "source_id": "coalesce(source_id, 0) as source_id",
    }
    if queue_id:
        return db.execute(f"""
            select id, status, execution_type, dry_run, priority, task_text,
                   {optional['safety_rules']}, {optional['target_files']},
                   {optional['suggested_commands']}, {optional['result_summary']},
                   {optional['source_table']}, {optional['source_id']}
            from dev_autopilot_queue
            where id=?
              and (status='approved' or dry_run=1)
            limit 1
        """, (queue_id,)).fetchone()
    return db.execute(f"""
        select id, status, execution_type, dry_run, priority, task_text,
               {optional['safety_rules']}, {optional['target_files']},
               {optional['suggested_commands']}, {optional['result_summary']},
               {optional['source_table']}, {optional['source_id']}
        from dev_autopilot_queue
        where status='approved'
           or (dry_run=1 and status in ('new', 'review', 'deferred'))
        order by case when status='approved' then 0 else 1 end,
                 priority desc,
                 id asc
        limit 1
    """).fetchone()


def recommend_from_codex_review(db: sqlite3.Connection) -> str:
    if not has_table(db, "codex_review_queue"):
        return ""
    cols = table_cols(db, "codex_review_queue")
    needed = {"id", "source_task_id", "review_status", "candidate_score", "review_summary", "next_prompt"}
    if not needed.issubset(cols):
        return ""
    row = db.execute("""
        select id, source_task_id, review_status, candidate_score, review_summary, next_prompt
        from codex_review_queue
        where review_status in ('queued', 'approved')
        order by case when review_status='approved' then 0 else 1 end,
                 candidate_score desc,
                 id asc
        limit 1
    """).fetchone()
    if not row:
        return ""
    return (
        f"codex_review_queue id={row['id']} status={row['review_status']} "
        f"task_id={row['source_task_id']} score={row['candidate_score']}: "
        f"{inline(row['review_summary'] or row['next_prompt'], 260)}"
    )


def recommend_from_revenue(db: sqlite3.Connection) -> str:
    if not has_table(db, "revenue_experiments"):
        return ""
    cols = table_cols(db, "revenue_experiments")
    needed = {"id", "status", "experiment_type", "title", "expected_cost", "router_task_id"}
    if not needed.issubset(cols):
        return ""
    row = db.execute("""
        select id, status, experiment_type, title, expected_cost, router_task_id, result_summary
        from revenue_experiments
        where status in ('new', 'review', 'approved')
          and coalesce(expected_cost, 0) = 0
        order by case when router_task_id is null then 0 else 1 end,
                 id desc
        limit 1
    """).fetchone()
    if not row:
        return ""
    routed = row["router_task_id"] if row["router_task_id"] is not None else "none"
    return (
        f"revenue_experiments id={row['id']} status={row['status']} "
        f"type={row['experiment_type']} cost={row['expected_cost']} router_task_id={routed}: "
        f"{inline(row['title'], 220)}"
    )


def recommend_from_router(db: sqlite3.Connection) -> str:
    if not has_table(db, "router_tasks"):
        return ""
    cols = table_cols(db, "router_tasks")
    needed = {"id", "target_bot", "mode", "status", "task_text"}
    if not needed.issubset(cols):
        return ""
    row = db.execute("""
        select id, target_bot, mode, status, task_text
        from router_tasks
        where status in ('new', 'review', 'approved', 'deferred')
          and (
            task_text like '%[WINNER_ONLY]%'
            or task_text like '%[REVENUE%'
            or task_text like '%codex%'
          )
        order by case status when 'approved' then 0 when 'review' then 1 when 'new' then 2 else 3 end,
                 id desc
        limit 1
    """).fetchone()
    if not row:
        return ""
    return (
        f"router_tasks id={row['id']} status={row['status']} "
        f"bot={row['target_bot']} mode={row['mode']}: {inline(row['task_text'], 260)}"
    )


def runtime_recommendation(db: sqlite3.Connection) -> tuple[str, list[str]]:
    facts = [
        count_by_status(db, "codex_review_queue", "review_status"),
        count_by_status(db, "revenue_experiments", "status"),
        count_by_status(db, "router_tasks", "status"),
    ]
    candidates = [
        recommend_from_revenue(db),
        recommend_from_codex_review(db),
        recommend_from_router(db),
    ]
    recommendation = next((c for c in candidates if c), "no safe recommendation found")
    return recommendation, facts


def default_safety_rules(extra_rules: str = "") -> str:
    lines = list(FORBIDDEN_ACTIONS)
    if extra_rules:
        lines.append("Queue-specific safety rules:")
        lines.extend(line for line in clean(extra_rules, 1200).splitlines() if line.strip())
    return "\n".join(f"- {line}" for line in lines)


def build_prompt(db: sqlite3.Connection, row: sqlite3.Row | None) -> str:
    recommendation, facts = runtime_recommendation(db)
    if row:
        task_text = clean(row["task_text"], 2200)
        execution_type = row["execution_type"]
        header = f"OpenClaw Dev Autopilot v1 queue_id={row['id']}"
        target_files = clean(row["target_files"], 1000) or "Read only the files needed for this task."
        suggested_commands = clean(row["suggested_commands"], 1000) or "Run the narrowest safe read-only or dry-run validation."
        result_summary = clean(row["result_summary"], 800) or "No previous result summary."
        source = f"{row['source_table']}:{row['source_id']}" if row["source_table"] else "dev_autopilot_queue"
        status_line = f"status={row['status']} dry_run={row['dry_run']} priority={row['priority']} source={source}"
        safety = default_safety_rules(row["safety_rules"])
    else:
        task_text = (
            "Inspect the runtime state below and propose the smallest safe next action. "
            "Do not execute it. Prefer observation-only or dry-run work."
        )
        execution_type = "observation"
        header = "OpenClaw Dev Autopilot v1 recommendation"
        target_files = "No direct file changes unless a later human-approved prompt asks for them."
        suggested_commands = "Use read-only sqlite SELECTs, log tails with secret redaction, and dry-run commands only."
        result_summary = "Generated from runtime state because no approved/dry-run dev_autopilot_queue item was available."
        status_line = "status=recommendation dry_run=1 priority=runtime"
        safety = default_safety_rules("")

    return f"""{header}

Purpose:
Use this prompt in Codex manually. The autopilot generated this prompt only; it did not start Codex.

Selected task:
- {status_line}
- execution_type={execution_type}

Task:
{task_text}

Target files:
{target_files}

Suggested commands:
{suggested_commands}

Runtime recommendation:
{recommendation}

Runtime facts:
{chr(10).join('- ' + fact for fact in facts)}

Safety rules:
{safety}

Expected response:
- State what you inspected.
- State any files changed, or say none.
- State validation results.
- State remaining risk and the next human approval needed.

Previous result summary:
{result_summary}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a safe Codex prompt from OpenClaw dev runtime state.")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--queue-id", type=int, default=0)
    args = parser.parse_args()

    with connect(args.db_path) as db:
        row = pick_autopilot_item(db, args.queue_id)
        print(build_prompt(db, row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
