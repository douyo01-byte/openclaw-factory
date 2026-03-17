from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 120

def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def main():
    while True:
        try:
            con = connect()
            c = con.cursor()
            rows = c.execute("""
                select id, coalesce(priority,0) as priority, coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_terminal_executor_bridge_v1'
                  and coalesce(decision_note,'') like '%terminal_executor_ready%'
                  and (
                    coalesce(priority,0) < 85
                    or coalesce(decision_note,'') not like '%terminal_executor_priority_fixed_85%'
                  )
                order by id desc
                limit 20
            """).fetchall()

            fixed = 0
            for r in rows:
                note = r["decision_note"]
                if "terminal_executor_priority_fixed_85" not in note:
                    note = (note + " | terminal_executor_priority_fixed_85").strip(" |")
                c.execute("""
                    update dev_proposals
                    set
                      priority=85,
                      decision_note=?
                    where id=?
                """, (note, r["id"]))
                fixed += c.rowcount

            con.commit()
            con.close()
            print(f"{datetime.now().isoformat()} fixed={fixed}", flush=True)
        except Exception as e:
            print(f"ceo_terminal_executor_priority_fixer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
