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
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_guarded_mainline_promoter_v1'
                  and coalesce(status,'')='new'
                order by id asc
                limit 20
            """).fetchall()

            fixed = 0
            for r in rows:
                note = r["decision_note"] or ""
                p = int(r["priority"] or 0)
                new_p = p
                if "priority_fixed_85" in note:
                    new_p = max(new_p, 85)
                if "guard_executor_ready" in note:
                    new_p = max(new_p, 85)
                if new_p != p or "guard_mainline_priority_synced" not in note:
                    new_note = note
                    if "guard_mainline_priority_synced" not in new_note:
                        new_note = (new_note + " | guard_mainline_priority_synced").strip(" |")
                    c.execute("""
                        update dev_proposals
                        set priority=?,
                            decision_note=?
                        where id=?
                    """, (new_p, new_note, r["id"]))
                    fixed += 1

            con.commit()
            con.close()

            if fixed:
                print(f"{datetime.now().isoformat()} fixed={fixed}", flush=True)
        except Exception as e:
            print(f"guarded_mainline_priority_fixer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
