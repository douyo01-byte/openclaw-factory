from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 120

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

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
                  coalesce(status,'') as status,
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(branch_name,'') as branch_name
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_executor_guarded_promoter_v1'
                  and coalesce(project_decision,'')='selected_now'
                  and coalesce(decision_note,'') like '%final_guard_selected%'
                  and coalesce(decision_note,'') not like '%final_guard_bridged%'
                order by id asc
                limit 20
            """).fetchall()

            bridged = 0

            for r in rows:
                note = (r["decision_note"] or "").strip()
                if note:
                    new_note = note + " | final_guard_bridged"
                else:
                    new_note = "final_guard_bridged"

                branch_name = (r["branch_name"] or "").strip()
                if not branch_name:
                    branch_name = f"auto/ceo-final-guard-bridge-{r['id']}"
                branch_name = branch_name[:255]

                c.execute("""
                    insert into dev_proposals (
                      title,
                      description,
                      source_ai,
                      status,
                      priority,
                      project_decision,
                      decision_note,
                      target_system,
                      improvement_type,
                      branch_name,
                      created_at
                    ) values (
                      ?, ?, 'ceo_final_guard_bridge_v1', 'new',
                      ?, 'go', ?, ?, ?, ?, datetime('now')
                    )
                """, (
                    f"Executor最終候補本流投入 : {r['title']}",
                    r["description"],
                    max(int(r["priority"] or 0), 85),
                    f"final_guard_from={r['id']} | {note}" if note else f"final_guard_from={r['id']}",
                    r["target_system"],
                    r["improvement_type"],
                    branch_name,
                ))

                c.execute("""
                    update dev_proposals
                    set decision_note=?
                    where id=?
                """, (new_note, r["id"]))

                bridged += 1

            con.commit()
            con.close()

            if bridged:
                print(f"{datetime.now().isoformat()} bridged={bridged}", flush=True)

        except Exception as e:
            print(f"ceo_final_guard_bridge_error: {e}", flush=True)

        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
