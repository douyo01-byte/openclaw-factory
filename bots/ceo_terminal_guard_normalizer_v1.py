import os, sqlite3
from datetime import datetime

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    rows = c.execute("""
        select id, coalesce(decision_note,'') as note
        from dev_proposals
        where source_ai='ceo_terminal_guard_bridge_v1'
          and coalesce(status,'')='new'
          and coalesce(project_decision,'') in ('', 'go', 'selected_now')
          and (
            coalesce(priority,0)=0
            or coalesce(project_decision,'')<>'go'
            or coalesce(target_system,'')=''
            or coalesce(improvement_type,'')=''
            or coalesce(decision_note,'') not like '%terminal_guard_ready%'
          )
        order by id asc
    """).fetchall()
    n = 0
    for r in rows:
        note = r["note"]
        if "priority_fixed_85" in note or "terminal_executor_priority_fixed_85" in note or "terminal_guard_priority_synced" in note:
            priority = 85
        else:
            priority = 0
        if "terminal_guard_ready" not in note:
            note = (note + " | terminal_guard_ready").strip(" |")
        c.execute("""
            update dev_proposals
            set priority=?,
                project_decision='go',
                target_system=coalesce(nullif(target_system,''),'ceo_decision_layer_v1'),
                improvement_type=coalesce(nullif(improvement_type,''),'autonomous_planning'),
                decision_note=?
            where id=?
        """, (priority, note, r["id"]))
        n += 1
    con.commit()
    con.close()
    print(f"{datetime.now().isoformat()} normalized={n}")

if __name__ == "__main__":
    main()
