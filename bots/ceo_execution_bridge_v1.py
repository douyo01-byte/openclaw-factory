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

def normalize_branch(title: str, row_id: int) -> str:
    s = (title or "").lower()
    s = re.sub(r"昇\s*格\s*[:：]\s*", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9ぁ-んァ-ヶ一-龠\-]", "", s)
    s = s.strip("-")
    if not s:
        s = f"ceo-exec-{row_id}"
    return f"ceo-exec/{s[:48]}-{row_id}"

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
                where coalesce(source_ai,'')='ceo_growth_promoter_v1'
                  and coalesce(project_decision,'')='selected_now'
                  and coalesce(decision_note,'') not like '%bridged_to_mainline%';
            """).fetchall()

            bridged = 0
            for r in rows:
                branch = normalize_branch(r["title"], r["id"])
                new_title = f"CEO実行: {r['title']}"
                new_desc = (
                    (r["description"] or "").strip() + "\n\n" +
                    f"[bridge_from]={r['id']}\n" +
                    f"[bridge_reason]={r['decision_note'] or ''}\n" +
                    f"[target_system]={r['target_system'] or ''}\n" +
                    f"[improvement_type]={r['improvement_type'] or ''}"
                ).strip()

                c.execute("""
                    insert into dev_proposals
                    (
                      title, description, branch_name, status, risk_level,
                      created_at, source_ai, priority, target_system,
                      improvement_type, decision_note, project_decision
                    )
                    values (?, ?, ?, 'new', 'medium', datetime('now'),
                            'ceo_execution_bridge_v1', ?, ?, ?, ?, 'go')
                """, (
                    new_title,
                    new_desc,
                    branch,
                    int(r["priority"] or 0),
                    r["target_system"] or "",
                    r["improvement_type"] or "",
                    f"bridged_from={r['id']} | {r['decision_note'] or ''}",
                ))

                c.execute("""
                    update dev_proposals
                    set decision_note = trim(coalesce(decision_note,'') || ' | bridged_to_mainline')
                    where id = ?
                """, (r["id"],))

                bridged += 1

            con.commit()
            con.close()

            if bridged:
                print(f"{datetime.now().isoformat()} bridged={bridged}", flush=True)
        except Exception as e:
            print(f"execution_bridge_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
