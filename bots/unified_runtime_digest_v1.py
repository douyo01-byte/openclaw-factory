#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bots import telegram_digest_v1

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
WINDOW_MIN = int(os.environ.get("UNIFIED_RUNTIME_DIGEST_WINDOW_MIN", "60"))
DRY_RUN = os.environ.get("UNIFIED_RUNTIME_DIGEST_DRY_RUN", "1") != "0"
MAX_CHARS = int(os.environ.get("UNIFIED_RUNTIME_DIGEST_MAX_CHARS", "3500"))


def connect():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("pragma busy_timeout=30000")
    return db


def has_table(db, table: str) -> bool:
    row = db.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_cols(db, table: str) -> set[str]:
    if not has_table(db, table):
        return set()
    return {r["name"] for r in db.execute(f"pragma table_info({table})").fetchall()}


def require_schema(db):
    required = {
        "unified_runtime_digests": {"summary", "execution_section", "runtime_health_section", "sent_to_telegram"},
        "unified_runtime_digest_state": {"key", "value", "updated_at"},
    }
    for table, cols in required.items():
        present = table_cols(db, table)
        missing = sorted(cols - present)
        if missing:
            raise RuntimeError(
                f"schema_missing table={table} cols={','.join(missing)} "
                "apply migrations/20260513_unified_runtime_digest_v1.sql first"
            )


def compact(text: str, limit: int = 500) -> str:
    text = "\n".join(line.rstrip() for line in (text or "").strip().splitlines())
    return text[:limit]


def inline(text: str, limit: int = 180) -> str:
    return " ".join((text or "").replace("\r", "\n").replace("\n", " ").split())[:limit]


def is_winner_only_new_think(row) -> bool:
    return (
        (row["status"] or "") == "new"
        and (row["mode"] or "") == "THINK"
        and (row["task_text"] or "").startswith("[WINNER_ONLY]")
    )


def execution_priority(row) -> int:
    status = row["status"] or ""
    text = " ".join(
        [
            row["task_text"] or "",
            row["reply_text"] or "",
            row["result_text"] or "",
            row["validation_reason"] or "",
            row["exec_bridge_reason"] or "",
        ]
    ).lower()
    if status == "failed" or "risk" in text or "unknown mode" in text or "invalid arg" in text:
        return 0
    if "[exec]" in text or "exec result" in text:
        return 1
    if status == "done" or row["result_text"] or "artifact=" in text or "public_preview/" in text:
        return 2
    return 3


def format_execution_row(row, idx: int) -> str:
    family = telegram_digest_v1.task_family(row)
    instruction = inline(row["clean_prompt"] or row["task_text"], 150)
    execution = telegram_digest_v1.infer_execution([row])
    result = telegram_digest_v1.infer_result([row])
    risk = telegram_digest_v1.infer_risk([row])
    return "\n".join(
        [
            f"{idx}. {family} id={row['id']} status={row['status'] or '-'}",
            f"   instruction: {instruction}",
            f"   execution: {inline(execution, 180)}",
            f"   result: {inline(result, 220)}",
            f"   risk: {risk}",
        ]
    )


def q1(db, sql: str, params=(), default=0):
    try:
        row = db.execute(sql, params).fetchone()
        if row is None:
            return default
        return row[0]
    except sqlite3.Error:
        return default


def count_by_status(db, table: str, status_col: str) -> str:
    if not has_table(db, table) or status_col not in table_cols(db, table):
        return "not configured"
    rows = db.execute(f"""
        select coalesce({status_col}, '') as status, count(*) as n
        from {table}
        group by coalesce({status_col}, '')
        order by n desc, status asc
    """).fetchall()
    if not rows:
        return "none"
    return " / ".join(f"{r['status'] or '-'}={int(r['n'] or 0)}" for r in rows[:6])


def execution_section(db) -> str:
    if not has_table(db, "router_tasks"):
        return "Execution:\nrouter_tasks not configured"
    cols = table_cols(db, "router_tasks")
    needed = {"id", "parent_task_id", "task_role", "target_bot", "mode", "status", "task_text", "reply_text"}
    if not needed.issubset(cols):
        return "Execution:\nrouter_tasks schema incomplete"
    select_cols = {
        "clean_prompt": "coalesce(clean_prompt, '') as clean_prompt" if "clean_prompt" in cols else "'' as clean_prompt",
        "result_text": "coalesce(result_text, '') as result_text" if "result_text" in cols else "'' as result_text",
        "validation_reason": "coalesce(validation_reason, '') as validation_reason" if "validation_reason" in cols else "'' as validation_reason",
        "exec_bridge_reason": "coalesce(exec_bridge_reason, '') as exec_bridge_reason" if "exec_bridge_reason" in cols else "'' as exec_bridge_reason",
    }
    rows = db.execute(f"""
        select
          id,
          coalesce(parent_task_id, 0) as parent_task_id,
          coalesce(task_role, '') as task_role,
          coalesce(target_bot, '') as target_bot,
          coalesce(mode, '') as mode,
          coalesce(status, '') as status,
          coalesce(task_text, '') as task_text,
          {select_cols['clean_prompt']},
          coalesce(reply_text, '') as reply_text,
          {select_cols['result_text']},
          {select_cols['validation_reason']},
          {select_cols['exec_bridge_reason']},
          coalesce(updated_at, created_at, '') as ts
        from router_tasks
        where datetime(coalesce(updated_at, created_at)) >= datetime('now', ?)
        order by id asc
        limit 120
    """, (f"-{WINDOW_MIN} minutes",)).fetchall()
    if not rows:
        return "Execution:\nno material execution rows"

    return compact("Execution:\n" + telegram_digest_v1.build_digest(rows), 1500)


def runtime_health_section(db) -> tuple[str, str]:
    if not has_table(db, "runtime_health_scores"):
        return "Runtime health:\nnot configured", ""
    row = db.execute("""
        select
          count(*) as total,
          avg(health_score) as avg_health,
          sum(case when cleanup_priority >= 70 then 1 else 0 end) as cleanup_high,
          sum(case when zombie_score >= 70 then 1 else 0 end) as zombie_high,
          avg(case when core_weight >= 80 then health_score end) as core_avg
        from runtime_health_scores
    """).fetchone()
    watch = db.execute("""
        select program_key, health_score, cleanup_priority, score_reason
        from runtime_health_scores
        where core_weight >= 80
        order by health_score asc, program_key asc
        limit 3
    """).fetchall()
    lines = [
        "Runtime health:",
        (
            f"programs={int(row['total'] or 0)} "
            f"avg={float(row['avg_health'] or 0):.1f} "
            f"core_avg={float(row['core_avg'] or 0):.1f} "
            f"cleanup_high={int(row['cleanup_high'] or 0)} "
            f"zombie_high={int(row['zombie_high'] or 0)}"
        ),
    ]
    risk = ""
    for item in watch:
        lines.append(
            f"- {item['program_key']} health={float(item['health_score'] or 0):.1f} "
            f"cleanup={float(item['cleanup_priority'] or 0):.1f}"
        )
    if row["cleanup_high"] or row["zombie_high"]:
        risk = f"runtime cleanup_high={int(row['cleanup_high'] or 0)} zombie_high={int(row['zombie_high'] or 0)}"
    return "\n".join(lines), risk


def cleanup_section(db) -> str:
    lines = ["Cleanup:"]
    if has_table(db, "runtime_health_scores"):
        rows = db.execute("""
            select program_key, cleanup_priority, zombie_score, entropy_score, core_weight, score_reason
            from runtime_health_scores
            where cleanup_priority >= 40
            order by cleanup_priority desc, zombie_score desc, program_key asc
            limit 3
        """).fetchall()
        if rows:
            for row in rows:
                lines.append(
                    f"- {row['program_key']} cleanup={float(row['cleanup_priority'] or 0):.1f} "
                    f"zombie={float(row['zombie_score'] or 0):.1f} entropy={float(row['entropy_score'] or 0):.1f}"
                )
        else:
            lines.append("no high cleanup candidates")
    else:
        lines.append("runtime_health_scores not configured")
    if has_table(db, "runtime_pause_candidates"):
        lines.append("pause_queue: " + count_by_status(db, "runtime_pause_candidates", "approval_status"))
    return "\n".join(lines)


def codex_section(db) -> str:
    parts = ["Codex:"]
    parts.append("tasks: " + count_by_status(db, "codex_tasks", "status"))
    parts.append("review_queue: " + count_by_status(db, "codex_review_queue", "review_status"))
    if has_table(db, "codex_review_queue"):
        cols = table_cols(db, "codex_review_queue")
        if {"id", "review_status", "candidate_score"}.issubset(cols):
            row = db.execute("""
                select id, source_task_id, candidate_score
                from codex_review_queue
                where review_status='queued'
                order by candidate_score desc, id asc
                limit 1
            """).fetchone()
            if row:
                parts.append(
                    f"next_action: review queue_id={row['id']} task_id={row['source_task_id']} "
                    f"score={float(row['candidate_score'] or 0):.1f}"
                )
    if has_table(db, "codex_task_runs"):
        parts.append("runs: " + count_by_status(db, "codex_task_runs", "status"))
    return "\n".join(parts)


def revenue_section(db) -> str:
    parts = ["Revenue:"]
    if not has_table(db, "revenue_experiments"):
        parts.append("not configured")
        return "\n".join(parts)
    parts.append("experiments: " + count_by_status(db, "revenue_experiments", "status"))
    if has_table(db, "revenue_experiments") and "status" in table_cols(db, "revenue_experiments"):
        winner = q1(db, "select count(*) from revenue_experiments where status like '%winner%'")
        running = q1(db, "select count(*) from revenue_experiments where status in ('running','active')")
        if winner:
            parts.append(f"next_action: inspect {int(winner)} winner candidate experiment(s)")
        elif running:
            parts.append(f"next_action: monitor {int(running)} running experiment(s)")
        else:
            parts.append("next_action: queue next safe revenue experiment")
    if has_table(db, "revenue_learnings"):
        parts.append(f"learnings={q1(db, 'select count(*) from revenue_learnings')}")
    if has_table(db, "revenue_variant_groups"):
        parts.append("variant_groups: " + count_by_status(db, "revenue_variant_groups", "status"))
    return "\n".join(parts)


def trend_section(db) -> str:
    parts = ["Trend:"]
    if not has_table(db, "trend_items"):
        parts.append("not configured")
        return "\n".join(parts)
    parts.append(f"items={q1(db, 'select count(*) from trend_items')}")
    if has_table(db, "trend_proposals"):
        parts.append("proposals: " + count_by_status(db, "trend_proposals", "proposal_status"))
    return "\n".join(parts)


def risk_section(*sections: str) -> str:
    text = "\n".join(sections).lower()
    risks = []
    if "unknown mode" in text or "invalid arg" in text:
        risks.append("EXEC mode routing risk")
    if "schema_missing" in text:
        risks.append("schema migration risk")
    if "cleanup_high=0 zombie_high=0" not in text and "cleanup_high=" in text:
        risks.append("runtime cleanup queue requires review")
    if "not configured" in text:
        risks.append("some governance tables not configured")
    if not risks:
        risks.append("no material residual risk detected")
    return "Residual risk:\n" + "\n".join(f"- {risk}" for risk in risks[:5])


def topline(sections: dict[str, str]) -> str:
    status = "watch"
    risk_text = sections.get("risk", "")
    if "EXEC mode routing risk" in risk_text or "schema migration risk" in risk_text:
        status = "risk"
    return f"OpenClaw unified runtime digest\nwindow={WINDOW_MIN}m status={status}"


def build_digest(db) -> dict[str, str]:
    execution = execution_section(db)
    health, health_risk = runtime_health_section(db)
    cleanup = cleanup_section(db)
    codex = codex_section(db)
    revenue = revenue_section(db)
    trend = trend_section(db)
    risk = risk_section(execution, health, cleanup, codex, revenue, trend, health_risk)
    sections = {
        "execution": execution,
        "health": health,
        "cleanup": cleanup,
        "codex": codex,
        "revenue": revenue,
        "trend": trend,
        "risk": risk,
    }
    summary = topline(sections)
    full = "\n\n".join([summary, codex, revenue, execution, health, cleanup, trend, risk])
    if len(full) > MAX_CHARS:
        full = full[:MAX_CHARS] + "\n\n[truncated]"
    sections["summary"] = summary
    sections["full"] = full
    return sections


def record_digest(db, sections: dict[str, str]):
    db.execute("""
        insert into unified_runtime_digests
        (
          digest_type, window_minutes, summary, execution_section,
          runtime_health_section, cleanup_section, codex_section,
          revenue_section, trend_section, risk_section, sent_to_telegram, created_at
        )
        values
        ('dry_run', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))
    """, (
        WINDOW_MIN,
        sections["summary"],
        sections["execution"],
        sections["health"],
        sections["cleanup"],
        sections["codex"],
        sections["revenue"],
        sections["trend"],
        sections["risk"],
    ))


def run_once(record: bool = False) -> str:
    db = connect()
    try:
        require_schema(db)
        sections = build_digest(db)
        if record:
            record_digest(db, sections)
            db.commit()
        return sections["full"]
    finally:
        db.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Build a unified dry-run runtime digest.")
    parser.add_argument("--record", action="store_true", help="record digest snapshot in DB")
    parser.add_argument("--dry-run", action="store_true", default=DRY_RUN)
    return parser.parse_args()


def main():
    args = parse_args()
    text = run_once(record=args.record and not args.dry_run)
    print("[unified_runtime_digest_v1] dry_run digest_begin" if args.dry_run else "[unified_runtime_digest_v1] digest_begin")
    print(text)
    print("[unified_runtime_digest_v1] dry_run digest_end" if args.dry_run else "[unified_runtime_digest_v1] digest_end")


if __name__ == "__main__":
    main()
