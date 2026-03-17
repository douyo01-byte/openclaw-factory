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

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_executor_bridge_v1'
                  and coalesce(status,'')='new'
                  and coalesce(project_decision,'')='selected_now'
                  and coalesce(decision_note,'') not like '%final_executor_ready%'
                order by id asc
                limit 20
            """).fetchall()

            normalized = 0
            for r in rows:
                note = r["decision_note"] or ""
                if "final_executor_ready" not in note:
                    note = (note + " | final_executor_ready").strip(" |")
                c.execute("""
                    update dev_proposals
                    set
                      priority=case
                        when cast(coalesce(priority,0) as integer) < 85 then 85
                        else cast(coalesce(priority,0) as integer)
                      end,
                      project_decision='go',
                      decision_note=?
                    where id=?
                """, (note, r["id"]))
                normalized += 1

            con.commit()
            con.close()
            if normalized:
                print(f"{datetime.now().isoformat()} normalized={normalized}", flush=True)
        except Exception as e:
            print(f"final_executor_normalizer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
