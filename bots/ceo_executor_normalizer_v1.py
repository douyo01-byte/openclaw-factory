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
                  coalesce(branch_name,'') as branch_name,
                  coalesce(priority,0) as priority,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_mainline_promoter_v1'
                  and coalesce(status,'')='new'
                  and coalesce(decision_note,'') not like '%executor_ready%';
            """).fetchall()

            normalized = 0
            for r in rows:
                note = (r["decision_note"] or "").strip()
                if note:
                    note = note + " | executor_ready"
                else:
                    note = "executor_ready"

                c.execute("""
                    update dev_proposals
                    set
                      project_decision='go',
                      status='new',
                      priority=case
                        when coalesce(priority,0) < 85 then 85
                        else coalesce(priority,0)
                      end,
                      decision_note=?,
                      risk_level='medium',
                      processing=0
                    where id=?
                """, (note, r["id"]))
                normalized += 1

            con.commit()
            con.close()

            if normalized:
                print(f"{datetime.now().isoformat()} normalized={normalized}", flush=True)
        except Exception as e:
            print(f"executor_normalizer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
