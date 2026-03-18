#!/usr/bin/env python3
import os, sqlite3, datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    row = c.execute("""
        select
          id, title, source_ai, status,
          coalesce(priority,0) as priority,
          coalesce(project_decision,'') as project_decision,
          coalesce(decision_note,'') as decision_note,
          coalesce(target_system,'') as target_system,
          coalesce(improvement_type,'') as improvement_type,
          coalesce(branch_name,'') as branch_name
        from dev_proposals
        where id=2889
        limit 1
    """).fetchone()
    if not row:
        print("bridged=0 reason=no_source")
        con.close()
        return
    note = row["decision_note"] or ""
    if "terminal_guard_final_selected" not in note and row["project_decision"] != "selected_now":
        print("bridged=0 reason=not_selected")
        con.close()
        return
    exists = c.execute("""
        select 1
        from dev_proposals
        where source_ai='ceo_terminal_final_executor_bridge_v1'
          and coalesce(decision_note,'') like ?
        limit 1
    """, (f"%terminal_final_executor_from={row['id']}%",)).fetchone()
    if exists:
        print("bridged=0 reason=exists")
        con.close()
        return
    new_note = " | ".join(x for x in [
        f"terminal_final_executor_from={row['id']}",
        note
    ] if x)
    new_title = f"Terminal最終実行投入 : {row['title']}"
    c.execute("""
        insert into dev_proposals(
          title, source_ai, status, priority, project_decision,
          decision_note, target_system, improvement_type, branch_name,
          created_at
        ) values(?,?,?,?,?,?,?,?,?,?)
    """, (
        new_title,
        "ceo_terminal_final_executor_bridge_v1",
        "new",
        85 if (
            row["priority"] == 85
            or "priority_fixed_85" in note
            or "terminal_executor_priority_fixed_85" in note
            or "terminal_guard_priority_synced" in note
        ) else row["priority"],
        "go",
        new_note,
        row["target_system"],
        row["improvement_type"],
        row["branch_name"],
        datetime.datetime.now().isoformat(timespec="seconds"),
    ))
    c.execute("""
        update dev_proposals
        set decision_note = case
          when coalesce(decision_note,'') like '%terminal_final_executor_bridged%'
            then coalesce(decision_note,'')
          else coalesce(decision_note,'') || ' | terminal_final_executor_bridged'
        end
        where id=?
    """, (row["id"],))
    con.commit()
    print(f"bridged=1 source={row['id']}")
    con.close()

if __name__ == "__main__":
    main()
