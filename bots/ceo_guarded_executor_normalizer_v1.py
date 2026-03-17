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

def effective_priority(priority, note):
    p = int(priority or 0)
    t = note or ""
    if "priority_fixed_85" in t:
        p = max(p, 85)
    return p

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  coalesce(priority,0) as priority,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_executor_guarded_promoter_v1'
                  and coalesce(status,'')='new'
                  and coalesce(decision_note,'') not like '%guard_executor_ready%'
                order by id asc
                limit 20
            """).fetchall()

            fixed = 0
            for r in rows:
                p = effective_priority(r["priority"], r["decision_note"])
                note = r["decision_note"]
                if "guard_executor_ready" not in note:
                    note = (note + " | guard_executor_ready").strip(" |")
                c.execute("""
                    update dev_proposals
                    set priority=?,
                        project_decision='go',
                        decision_note=?
                    where id=?
                """, (p, note, r["id"]))
                fixed += 1

            con.commit()
            con.close()

            if fixed:
                print(f"{datetime.now().isoformat()} normalized={fixed}", flush=True)
        except Exception as e:
            print(f"guard_executor_normalizer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
