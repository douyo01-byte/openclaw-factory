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

            c.execute("""
                update dev_proposals
                set priority=85
                where id in (2846,2848)
                  and coalesce(priority,0) <> 85
            """)
            fixed = c.rowcount

            c.execute("""
                update dev_proposals
                set decision_note=
                    case
                      when coalesce(decision_note,'') like '%priority_fixed_85%' then decision_note
                      when coalesce(decision_note,'')='' then 'priority_fixed_85'
                      else decision_note || ' | priority_fixed_85'
                    end
                where id in (2846,2848)
            """)

            con.commit()
            con.close()

            if fixed:
                print(f"{datetime.now().isoformat()} fixed={fixed}", flush=True)
        except Exception as e:
            print(f"priority_fixer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
