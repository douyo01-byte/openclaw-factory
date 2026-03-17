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
                select
                  id,
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note
                from dev_proposals
                where coalesce(source_ai,'')='ceo_terminal_executor_bridge_v1'
                order by id desc
                limit 20
            """).fetchall()

            normalized = 0
            for r in rows:
                note = r["decision_note"] or ""
                if "terminal_executor_ready" in note and int(r["priority"] or 0) >= 85 and r["project_decision"] == "go":
                    continue

                fixed_note = note
                if "priority_fixed_85" in fixed_note and "terminal_executor_priority_synced" not in fixed_note:
                    fixed_note = (fixed_note + " | terminal_executor_priority_synced").strip(" |")
                if "terminal_executor_ready" not in fixed_note:
                    fixed_note = (fixed_note + " | terminal_executor_ready").strip(" |")

                c.execute("""
                    update dev_proposals
                    set
                      priority = case
                        when coalesce(priority,0) < 85 then 85
                        else priority
                      end,
                      project_decision = 'go',
                      decision_note = ?
                    where id = ?
                """, (fixed_note, r["id"]))
                normalized += 1

            con.commit()
            con.close()
            print(f"{datetime.now().isoformat()} normalized={normalized}", flush=True)
        except Exception as e:
            print(f"ceo_terminal_executor_normalizer_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
