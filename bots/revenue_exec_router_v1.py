#!/usr/bin/env python3
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)
PUBLIC_BASE_URL = os.environ.get("REVENUE_PUBLIC_BASE_URL", "https://douyo01-byte.github.io/openclaw-factory")
DISTRIBUTION_TYPES = ("telegram_post", "x_thread", "short_blog", "comparison_post", "reddit_style")

def con():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def has_table(db, name: str) -> bool:
    row = db.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (name,)
    ).fetchone()
    return row is not None

def table_cols(db, name: str) -> set[str]:
    if not has_table(db, name):
        return set()
    return {r["name"] for r in db.execute(f"pragma table_info({name})").fetchall()}

REQUIRED_SCHEMA = {
    "revenue_variant_groups": {
        "id", "opportunity_id", "experiment_id", "name", "strategy", "status",
        "winner_experiment_id", "digest_summary", "created_at", "updated_at",
    },
    "revenue_variant_metrics": {
        "id", "group_id", "experiment_id", "variant_key", "artifact_path",
        "views", "clicks", "telegram_clicks", "actions", "conversions",
        "ctr", "cvr", "score", "rank", "status", "source", "captured_at",
    },
    "revenue_distribution_tasks": {
        "id", "group_id", "experiment_id", "variant_key", "distribution_type",
        "traffic_source", "cta_url", "content", "artifact_path", "status",
        "created_at", "updated_at",
    },
    "revenue_memory_patterns": {
        "id", "memory_type", "pattern", "horizon_type", "economic_summary",
        "portfolio_summary", "domain_summary", "evidence", "score",
        "reuse_count", "last_used_at", "created_at", "updated_at",
    },
}

def require_schema(db):
    for table, required in REQUIRED_SCHEMA.items():
        missing = sorted(required - table_cols(db, table))
        if missing:
            raise RuntimeError(
                f"schema_missing table={table} cols={','.join(missing)} "
                "apply migrations/20260513_revenue_core_schema_v2.sql first"
            )

def ensure_schema(db):
    require_schema(db)
    db.execute("""
        update revenue_memory_patterns
        set score=score * 0.85,
            updated_at=datetime('now')
        where horizon_type='short_term'
          and coalesce(nullif(last_used_at, ''), created_at) < datetime('now', '-14 days')
    """)
    db.execute("""
        update revenue_memory_patterns
        set score=score * 0.95,
            updated_at=datetime('now')
        where horizon_type='mid_term'
          and coalesce(nullif(last_used_at, ''), created_at) < datetime('now', '-30 days')
    """)
    db.execute("""
        update revenue_memory_patterns
        set score=score * 0.98,
            updated_at=datetime('now')
        where horizon_type='long_term'
          and coalesce(nullif(last_used_at, ''), created_at) < datetime('now', '-60 days')
    """)

def extract_experiment_id(task_text: str) -> int:
    m = re.search(r"Experiment:\s*- id:\s*(\d+)", task_text or "", re.S)
    return int(m.group(1)) if m else 0

def memory_hints(db, limit: int = 5) -> str:
    rows = db.execute("""
        select id, memory_type, pattern, horizon_type, economic_summary, portfolio_summary, domain_summary
        from revenue_memory_patterns
        where score > 0.1
        order by score desc, reuse_count desc, id asc
        limit ?
    """, (limit,)).fetchall()
    if not rows:
        return ""
    ids = [r["id"] for r in rows]
    db.execute(f"""
        update revenue_memory_patterns
        set reuse_count=reuse_count+1,
            last_used_at=datetime('now'),
            updated_at=datetime('now')
        where id in ({",".join("?" for _ in ids)})
    """, ids)
    return " / ".join(
        f"{r['horizon_type']}:{r['memory_type']}={r['pattern']}"
        + (f" ({r['economic_summary']})" if r["economic_summary"] else "")
        + (f" ({r['portfolio_summary']})" if r["portfolio_summary"] else "")
        + (f" ({r['domain_summary']})" if r["domain_summary"] else "")
        for r in rows
    )

def make_exec_text(exp, variant_key: str, hints: str) -> str:
    hint_line = f" / MEMORY_HINTS: {hints}" if hints else ""
    return f"""[EXEC]
script=run_python.sh
arg=mode=lpgen_exec;task=[REVENUE_VARIANT {variant_key}] {exp['title']} / 仮説: {exp['hypothesis']} / CTAリンクには variant_id={variant_key} を入れる / track.js を読み込む / Telegram導線・SNS訴求・CTAを含むLP案を成果物化{hint_line}
"""

def cta_url(variant_key: str, distribution_type: str) -> str:
    return f"{PUBLIC_BASE_URL}?variant_id={variant_key}&traffic_source={distribution_type}"

def distribution_content(title: str, variant_key: str, distribution_type: str, url: str, hints: str) -> str:
    hint = f"\nMEMORY_HINTS: {hints}" if hints else ""
    return (
        f"[{distribution_type}] variant={variant_key}\n"
        f"{title}\n"
        f"CTA: {url}\n"
        "track: /track.js sends variant_id and traffic_source"
        f"{hint}"
    )

def main():
    db = con()
    ensure_schema(db)

    row = db.execute("""
        select id, task_text
        from router_tasks
        where status='new'
          and task_text like '%[REVENUE_CORE]%'
        order by id asc
        limit 1
    """).fetchone()

    if not row:
        print("no revenue core")
        return

    exp_id = extract_experiment_id(row["task_text"])
    exp = db.execute("""
        select *
        from revenue_experiments
        where id=?
    """, (exp_id,)).fetchone()

    if not exp:
        print(f"missing revenue experiment id={exp_id}", flush=True)
        return

    cur = db.execute("""
        insert into revenue_variant_groups
        (opportunity_id, experiment_id, name, strategy, status, created_at, updated_at)
        values
        (?, ?, ?, 'epsilon_greedy', 'active', datetime('now'), datetime('now'))
    """, (exp["opportunity_id"], exp["id"], f"revenue_exp_{exp['id']}_lp_bandit"))
    group_id = cur.lastrowid
    hints = memory_hints(db)

    child_ids = []
    for variant_key in ("A", "B", "C"):
        if variant_key == "A":
            variant_exp_id = exp["id"]
        else:
            cur = db.execute("""
                insert into revenue_experiments
                (
                  opportunity_id,
                  experiment_type,
                  title,
                  hypothesis,
                  validation_method,
                  expected_signal,
                  expected_cost,
                  expected_validation_hours,
                  status,
                  created_at,
                  updated_at
                )
                values
                (?, ?, ?, ?, ?, ?, ?, ?, 'routed', datetime('now'), datetime('now'))
            """, (
                exp["opportunity_id"],
                f"{exp['experiment_type']}_variant",
                f"{exp['title']} variant {variant_key}",
                exp["hypothesis"],
                exp["validation_method"],
                exp["expected_signal"],
                exp["expected_cost"],
                exp["expected_validation_hours"],
            ))
            variant_exp_id = cur.lastrowid

        exec_text = make_exec_text(exp, variant_key, hints)
        cur = db.execute("""
            insert into router_tasks
            (
              parent_task_id,
              target_bot,
              mode,
              status,
              task_text,
              created_at,
              updated_at
            )
            values
            (
              ?,
              'ops_exec',
              'EXEC',
              'new',
              ?,
              datetime('now'),
              datetime('now')
            )
        """, (row["id"], exec_text))
        child_ids.append(str(cur.lastrowid))
        db.execute("""
            insert into revenue_variant_metrics
            (group_id, experiment_id, variant_key, status, source, captured_at)
            values
            (?, ?, ?, 'active', 'router_seed', datetime('now'))
            on conflict(group_id, experiment_id) do update set
              variant_key=excluded.variant_key,
              status='active',
              captured_at=datetime('now')
        """, (group_id, variant_exp_id, variant_key))
        for distribution_type in DISTRIBUTION_TYPES:
            url = cta_url(variant_key, distribution_type)
            db.execute("""
                insert into revenue_distribution_tasks
                (
                  group_id,
                  experiment_id,
                  variant_key,
                  distribution_type,
                  traffic_source,
                  cta_url,
                  content,
                  status,
                  created_at,
                  updated_at
                )
                values
                (?, ?, ?, ?, ?, ?, ?, 'planned', datetime('now'), datetime('now'))
                on conflict(group_id, experiment_id, distribution_type) do update set
                  cta_url=excluded.cta_url,
                  content=excluded.content,
                  updated_at=datetime('now')
            """, (
                group_id,
                variant_exp_id,
                variant_key,
                distribution_type,
                distribution_type,
                url,
                distribution_content(exp["title"], variant_key, distribution_type, url, hints),
            ))

    db.execute("""
        update router_tasks
        set status='done',
            reply_text=?,
            updated_at=datetime('now')
        where id=?
    """, (f"REVENUE_BANDIT_ROUTED group_id={group_id} child_ids={','.join(child_ids)}", row["id"]))

    db.execute("""
        update revenue_experiments
        set status='routed',
            updated_at=datetime('now')
        where id=?
    """, (exp["id"],))

    db.commit()

    print(
        f"routed revenue bandit parent={row['id']} group_id={group_id} children={','.join(child_ids)}",
        flush=True
    )

if __name__ == "__main__":
    main()
