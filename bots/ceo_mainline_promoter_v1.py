from __future__ import annotations
import os
import re
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

def make_branch(title: str, row_id: int) -> str:
    s = (title or "").lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9ぁ-んァ-ヶ一-龠\-]", "", s)
    s = s.strip("-")
    if not s:
        s = f"mainline-{row_id}"
    return f"mainline/{s[:48]}-{row_id}"

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()

            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(description,'') as description,
                  coalesce(priority,0) as priority,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_execution_bridge_v1'
                  and coalesce(status,'')='new'
                  and coalesce(decision_note,'') not like '%promoted_to_executor_mainline%'
                order by priority desc, id asc
                limit 5;
            """).fetchall()

            promoted = 0
            for r in rows:
                branch = make_branch(r["title"], r["id"])
                title = f"Mainline実行: {r['title']}"
                desc = (
                    (r["description"] or "").strip() + "\n\n" +
                    f"[mainline_from]={r['id']}\n" +
                    f"[target_system]={r['target_system'] or ''}\n" +
                    f"[improvement_type]={r['improvement_type'] or ''}\n" +
                    f"[reason]={r['decision_note'] or ''}"
                ).strip()

                c.execute("""
                    insert into dev_proposals
                    (
                      title, description, branch_name, status, risk_level,
                      created_at, source_ai, priority, target_system,
                      improvement_type, decision_note, project_decision
                    )
                    values (?, ?, ?, 'new', 'medium', datetime('now'),
                            'ceo_mainline_promoter_v1', ?, ?, ?, ?, 'go')
                """, (
                    title,
                    desc,
                    branch,
                    int(r["priority"] or 0),
                    r["target_system"] or "",
                    r["improvement_type"] or "",
                    f"executor_mainline_from={r['id']} | {r['decision_note'] or ''}",
                ))

                c.execute("""
                    update dev_proposals
                    set decision_note = trim(coalesce(decision_note,'') || ' | promoted_to_executor_mainline')
                    where id=?
                """, (r["id"],))

                promoted += 1

            con.commit()
            con.close()

            if promoted:
                print(f"{datetime.now().isoformat()} promoted={promoted}", flush=True)
        except Exception as e:
            print(f"mainline_promoter_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
