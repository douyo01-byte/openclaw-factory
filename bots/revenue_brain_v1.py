#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)

def con():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def main():
    db = con()

    opp = db.execute("""
        select *
        from revenue_opportunities
        where status in ('new','active')
        order by total_score desc, id asc
        limit 1
    """).fetchone()

    if not opp:
        print("[revenue_brain_v1] no opportunity", flush=True)
        return

    exp = db.execute("""
        select *
        from revenue_experiments
        where opportunity_id=?
          and status in ('new','planned')
        order by id asc
        limit 1
    """, (opp["id"],)).fetchone()

    if not exp:
        print(f"[revenue_brain_v1] no experiment opportunity_id={opp['id']}", flush=True)
        return

    task_text = f"""[REVENUE_CORE]
目的: 利益期待値が高い案件だけを前に進める。
禁止: runbook生成だけで止まること。必ず公開物・導線・検証可能な成果物に落とす。

Opportunity:
- id: {opp['id']}
- title: {opp['title']}
- rationale: {opp['rationale']}
- total_score: {opp['total_score']}

Experiment:
- id: {exp['id']}
- type: {exp['experiment_type']}
- title: {exp['title']}
- hypothesis: {exp['hypothesis']}
- validation_method: {exp['validation_method']}
- expected_signal: {exp['expected_signal']}

次の1手:
この実験を実行可能な最小成果物に分解し、Codex/ops_execで実装可能なEXECタスクを1つ作れ。
"""

    cur = db.execute("""
        insert into router_tasks
        (target_bot, mode, status, task_text, created_at, updated_at)
        values
        ('kaikun04', 'THINK', 'new', ?, datetime('now'), datetime('now'))
    """, (task_text,))

    router_task_id = cur.lastrowid

    db.execute("""
        update revenue_experiments
        set status='routed',
            router_task_id=?,
            updated_at=datetime('now')
        where id=?
    """, (router_task_id, exp["id"]))

    db.execute("""
        update revenue_opportunities
        set status='active',
            updated_at=datetime('now')
        where id=?
    """, (opp["id"],))

    db.commit()
    print(f"[revenue_brain_v1] routed opportunity_id={opp['id']} experiment_id={exp['id']} router_task_id={router_task_id}", flush=True)

if __name__ == "__main__":
    main()
