import os
import re
import sqlite3
import time
from datetime import datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def slug(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or "self-improve"

def choose_target(pattern_key: str) -> tuple[str, str]:
    k = (pattern_key or "").strip().lower()
    if k == "watcher":
        return "watcher", "observability"
    if k == "db":
        return "db", "reliability"
    if k == "health":
        return "healthcheck", "automation"
    if k == "log":
        return "logging", "observability"
    return "core", "automation"

def proposal_exists(c, title: str) -> bool:
    row = c.execute("""
        select id
        from dev_proposals
        where title=?
          and coalesce(status,'') not in ('merged','closed')
        order by id desc
        limit 1
    """, (title,)).fetchone()
    return row is not None

def insert_proposal(c, title: str, description: str, target_system: str, improvement_type: str):
    branch_name = f"dev/{slug(title)[:48]}"
    c.execute("""
        insert into dev_proposals(
          title,
          description,
          branch_name,
          status,
          risk_level,
          project_decision,
          dev_stage,
          pr_status,
          spec_stage,
          spec,
          category,
          target_system,
          improvement_type,
          quality_score,
          priority,
          score,
          guard_status,
          decision_note,
          source_ai,
          confidence,
          result_score,
          result_note,
          created_at,
          target_policy
        ) values(
          ?, ?, ?, 'approved', 'medium',
          'execute_now', 'execute_now', '', '', ?,
          'self_improvement', ?, ?, 0, 80, 0, 'safe', ?, 'self_improve', 0.9, 0, '', datetime('now'), ''
        )
    """, (
        title,
        description,
        branch_name,
        description,
        target_system,
        improvement_type,
        "generated from learning_patterns + supply_bias"
    ))
    return c.lastrowid

def run_once():
    c = conn()
    try:
        rows = c.execute("""
            select
              lp.pattern_key,
              lp.pattern_type,
              coalesce(lp.weight,0) as pattern_weight,
              coalesce(lp.sample_count,0) as sample_count,
              coalesce(sb.weight,0) as bias_weight
            from learning_patterns lp
            left join supply_bias sb
              on sb.bias_type = lp.pattern_type
             and sb.bias_key = lp.pattern_key
            where coalesce(lp.sample_count,0) >= 5
            order by coalesce(sb.weight,0) desc, coalesce(lp.weight,0) desc, coalesce(lp.sample_count,0) desc
            limit 10
        """).fetchall()

        inserted = 0
        for r in rows:
            pattern_key = str(r["pattern_key"] or "").strip()
            target_system, improvement_type = choose_target(pattern_key)

            title = f"Self improve {pattern_key} loop"
            description = (
                f"learning_patterns と supply_bias で {pattern_key} が高重み。"
                f"OpenClaw 自体の {pattern_key} 系改善を優先し、"
                f"成功パターン寄りの安定化・自動化を進める。"
            )

            if proposal_exists(c, title):
                continue

            insert_proposal(c, title, description, target_system, improvement_type)
            inserted += 1

        c.commit()
        print(f"self_improvement_inserted={inserted}", flush=True)
    finally:
        c.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(300)
