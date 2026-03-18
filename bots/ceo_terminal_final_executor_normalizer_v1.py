#!/usr/bin/env python3
import os, sqlite3, datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    rows = c.execute("""
        select
          id,
          coalesce(priority,0) as priority,
          coalesce(project_decision,'') as project_decision,
          coalesce(decision_note,'') as decision_note
        from dev_proposals
        where source_ai='ceo_terminal_final_executor_bridge_v1'
          and coalesce(status,'')='new'
    """).fetchall()
    fixed = 0
    for r in rows:
        note = r["decision_note"] or ""
        want85 = (
            r["priority"] == 85
            or "priority_fixed_85" in note
            or "terminal_executor_priority_fixed_85" in note
            or "terminal_guard_priority_synced" in note
            or "terminal_guard_final_selected" in note
        )
        new_priority = 85 if want85 else r["priority"]
        new_note = note if "terminal_final_executor_ready" in note else (note + " | terminal_final_executor_ready" if note else "terminal_final_executor_ready")
        if new_priority != r["priority"] or new_note != note or r["project_decision"] != "go":
            c.execute("""
                update dev_proposals
                set priority=?,
                    project_decision='go',
                    decision_note=?
                where id=?
            """, (new_priority, new_note, r["id"]))
            fixed += 1
    con.commit()
    print(f"{datetime.datetime.now().isoformat()} normalized={fixed}")
    con.close()

if __name__ == "__main__":
    main()
