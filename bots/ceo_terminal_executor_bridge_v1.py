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

def ensure_branch_name(row):
    bn = (row["branch_name"] or "").strip()
    if bn:
        return bn
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    target = (row["target_system"] or "unknown").replace(" ", "_")
    return f"ceo-terminal-exec/{target}-{row['id']}-{ts}"

def main():
    while True:
        try:
            con = connect()
            c = con.cursor()

            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(source_ai,'') as source_ai,
                  coalesce(status,'') as status,
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(branch_name,'') as branch_name,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_guard_bridge_v1'
                  and coalesce(project_decision,'')='selected_now'
                order by id desc
                limit 20
            """).fetchall()

            promoted = 0
            for r in rows:
                note = r["decision_note"] or ""
                if "terminal_executor_bridged" in note:
                    continue

                branch_name = ensure_branch_name(r)
                new_title = f"Executor最終実行投入 : {r['title']}"
                new_note = (
                    f"terminal_executor_from={r['id']} | "
                    f"{note}"
                ).strip()

                c.execute("""
                    insert into dev_proposals (
                      title, source_ai, status, priority, project_decision,
                      decision_note, target_system, improvement_type,
                      branch_name, created_at
                    ) values (?, ?, 'new', ?, 'go', ?, ?, ?, ?, datetime('now','localtime'))
                """, (
                    new_title,
                    "ceo_terminal_executor_bridge_v1",
                    int(r["priority"] or 0),
                    new_note,
                    r["target_system"],
                    r["improvement_type"],
                    branch_name,
                ))

                updated_note = note
                if "terminal_executor_bridged" not in updated_note:
                    updated_note = (updated_note + " | terminal_executor_bridged").strip(" |")
                c.execute("""
                    update dev_proposals
                    set decision_note=?, branch_name=?
                    where id=?
                """, (updated_note, branch_name, r["id"]))
                promoted += 1

            con.commit()
            con.close()
            print(f"{datetime.now().isoformat()} bridged={promoted}", flush=True)
        except Exception as e:
            print(f"ceo_terminal_executor_bridge_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
