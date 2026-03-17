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
                  title,
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(branch_name,'') as branch_name,
                  coalesce(status,'') as status
                from dev_proposals
                where coalesce(source_ai,'')='ceo_terminal_executor_bridge_v1'
                  and coalesce(project_decision,'') in ('selected_now','go')
                  and coalesce(decision_note,'') like '%terminal_executor_selected%'
                  and coalesce(decision_note,'') not like '%terminal_guard_promoted%'
                order by id desc
                limit 1
            """).fetchall()

            promoted = 0

            for r in rows:
                note = r["decision_note"]
                src_id = r["id"]

                new_note = (
                    f"terminal_guard_from={src_id} | " + note
                ).strip(" |")

                c.execute("""
                    insert into dev_proposals (
                      title,
                      source_ai,
                      status,
                      priority,
                      project_decision,
                      decision_note,
                      target_system,
                      improvement_type,
                      branch_name
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"Executor最終実行候補ガード投入 : {r['title']}",
                    "ceo_terminal_executor_guarded_promoter_v1",
                    "new",
                    max(int(r["priority"]), 85),
                    "go",
                    new_note,
                    r["target_system"],
                    r["improvement_type"],
                    r["branch_name"],
                ))

                src_note = note
                if "terminal_guard_promoted" not in src_note:
                    src_note = (src_note + " | terminal_guard_promoted").strip(" |")

                c.execute("""
                    update dev_proposals
                    set decision_note=?
                    where id=?
                """, (src_note, src_id))

                promoted += 1

            con.commit()
            con.close()
            print(f"{datetime.now().isoformat()} promoted={promoted}", flush=True)
        except Exception as e:
            print(f"ceo_terminal_executor_guarded_promoter_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
