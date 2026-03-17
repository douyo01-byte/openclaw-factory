from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 300

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def exists_same_title(c, title: str) -> bool:
    r = c.execute("""
        select 1
        from dev_proposals
        where coalesce(title,'')=?
        limit 1
    """, (title,)).fetchone()
    return r is not None

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()

            row = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(description,'') as description,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_growth_planner_v1'
                  and coalesce(project_decision,'')='go'
                order by coalesce(priority,0) desc, id desc
                limit 1
            """).fetchone()

            inserted = 0

            if row:
                promoted_title = f"昇 格 : {row['title']}"
                if not exists_same_title(c, promoted_title):
                    c.execute("""
                        insert into dev_proposals
                        (
                          title, description, branch_name, status, risk_level, created_at,
                          source_ai, target_system, improvement_type, priority, decision_note
                        )
                        values
                        (
                          ?, ?, ?, 'new', 'medium', datetime('now'),
                          'ceo_growth_promoter_v1', ?, ?, ?, ?
                        )
                    """, (
                        promoted_title,
                        (row["description"] or row["title"] or "") + " | promoted_from_ceo_growth_digest",
                        f"ceo-growth-promoted-{row['id']}",
                        row["target_system"] or "ceo_decision_layer_v1",
                        row["improvement_type"] or "autonomous_planning",
                        max(int(row["priority"] or 0), 80),
                        f"promoted_from={row['id']} | {row['decision_note'] or ''}",
                    ))
                    inserted = 1

            con.commit()
            con.close()

            if inserted:
                print(f"{datetime.now().isoformat()} promoted=1", flush=True)
        except Exception as e:
            print(f"growth_promoter_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
