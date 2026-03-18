#!/usr/bin/env python3
import os, sqlite3, datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def score_row(r):
    note = r["decision_note"] or ""
    s = 0
    s += int(r["priority"] or 0)
    if r["project_decision"] == "go":
        s += 20
    if "terminal_final_executor_ready" in note:
        s += 25
    if "terminal_guard_final_selected" in note:
        s += 20
    if "terminal_guard_selected" in note:
        s += 10
    if "terminal_executor_selected" in note:
        s += 10
    if "terminal_final_executor_selected" in note:
        s -= 1000
    return s

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    rows = c.execute("""
        select
          id, title, source_ai,
          coalesce(priority,0) as priority,
          coalesce(project_decision,'') as project_decision,
          coalesce(decision_note,'') as decision_note,
          coalesce(target_system,'') as target_system,
          coalesce(improvement_type,'') as improvement_type,
          coalesce(branch_name,'') as branch_name,
          coalesce(created_at,'') as created_at
        from dev_proposals
        where source_ai='ceo_terminal_final_executor_bridge_v1'
          and coalesce(status,'')='new'
    """).fetchall()

    ranked = sorted([(score_row(r), r) for r in rows], key=lambda x: (-x[0], -x[1]["id"]))
    selected_id = "none"

    if ranked and ranked[0][0] > 0:
        selected = ranked[0][1]
        note = selected["decision_note"] or ""
        if "terminal_final_executor_selected" not in note:
            note = note + " | terminal_final_executor_selected" if note else "terminal_final_executor_selected"
        c.execute("""
            update dev_proposals
            set
              priority = case
                when (
                  coalesce(priority,0)=85
                  or coalesce(decision_note,'') like '%priority_fixed_85%'
                  or coalesce(decision_note,'') like '%terminal_executor_priority_fixed_85%'
                  or coalesce(decision_note,'') like '%terminal_guard_priority_synced%'
                  or coalesce(decision_note,'') like '%terminal_guard_final_selected%'
                )
                then 85
                else coalesce(priority,0)
              end,
              project_decision='selected_now',
              decision_note=?
            where id=?
        """, (note, selected["id"]))
        con.commit()
        selected_id = str(selected["id"])

    path = "reports/audit_20260317/ceo_terminal_final_executor_selection.md"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# CEO Terminal Final Executor Selection ({datetime.datetime.now()})\n")
        f.write(f"- selected_id: {selected_id}\n")
        f.write("| rank | score | id | source_ai | priority | title |\n")
        f.write("|---:|---:|---:|---|---:|---|\n")
        for i, (score, r) in enumerate(ranked[:10], 1):
            title = (r["title"] or "").replace("\n", " ").replace("|", " ")
            f.write(f"| {i} | {score} | {r['id']} | {r['source_ai']} | {r['priority']} | {title} |\n")
    print(f"ranked={len(ranked)}")
    con.close()

if __name__ == "__main__":
    main()
