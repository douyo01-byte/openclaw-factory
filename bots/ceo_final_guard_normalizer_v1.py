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
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_guard_bridge_v1'
                  and coalesce(status,'')='new'
                  and coalesce(decision_note,'') not like '%final_guard_ready%'
                order by id asc
                limit 20
            """).fetchall()

            fixed = 0
            for r in rows:
                note = r["decision_note"] or ""
                if "priority_fixed_85" in note or "final_executor_ready" in note:
                    new_priority = max(int(r["priority"] or 0), 85)
                else:
                    new_priority = int(r["priority"] or 0)
                if "final_guard_ready" not in note:
                    note = (note + " | final_guard_ready").strip(" |")
                c.execute("""
                    update dev_proposals
                    set priority=?,
                        project_decision='go',
                        decision_note=?
                    where id=?
                """, (new_priority, note, r["id"]))
                fixed += 1

            con.commit()
            con.close()
            if fixed:
                print(f"{datetime.now().isoformat()} normalized={fixed}", flush=True)
        except Exception as e:
            print(f"ceo_final_guard_normalizer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
