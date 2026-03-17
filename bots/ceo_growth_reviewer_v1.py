from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 180

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def classify(row):
    title = row["title"] or ""
    target = row["target_system"] or ""
    imp = row["improvement_type"] or ""
    prio = int(row["priority"] or 0)

    decision = "go"
    note = "growth_review_ok"
    new_priority = prio

    if target in ("ceo_interface", "web_dashboard", "ceo_decision_layer_v1"):
        new_priority = max(new_priority, 85)
        note = "ceo_human_interface_priority"
        decision = "go"
    elif target == "ai_employee_factory":
        new_priority = max(new_priority, 78)
        note = "specialist_bot_expansion_candidate"
        decision = "go"
    elif imp in ("org_expansion",):
        new_priority = max(new_priority, 74)
        note = "org_growth_candidate"
        decision = "go"

    return new_priority, decision, note

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(priority,0) as priority,
                  coalesce(source_ai,'') as source_ai,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_growth_planner_v1'
                  and coalesce(project_decision,'')=''
                order by id asc
                limit 50
            """).fetchall()

            reviewed = 0
            for r in rows:
                new_priority, decision, note = classify(r)
                c.execute("""
                    update dev_proposals
                    set priority=?,
                        project_decision=?,
                        decision_note=?
                    where id=?
                """, (new_priority, decision, note, r["id"]))
                reviewed += 1

            con.commit()
            con.close()

            if reviewed:
                print(f"{datetime.now().isoformat()} reviewed={reviewed}", flush=True)
        except Exception as e:
            print(f"growth_reviewer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
