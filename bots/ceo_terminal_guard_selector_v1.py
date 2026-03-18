import os, sqlite3, time, datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def score_row(r):
    s = 0
    note = r["decision_note"] or ""
    p = int(r["priority"] or 0)

    if p == 0 and (
        "priority_fixed_85" in note
        or "terminal_executor_priority_fixed_85" in note
        or "terminal_guard_priority_synced" in note
    ):
        p = 85

    s += p

    if "terminal_guard_ready" in note:
        s += 25
    if "terminal_guard_priority_synced" in note:
        s += 20

    if (r["project_decision"] or "") == "selected_now":
        s -= 999

    return s

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()

    rows = c.execute("""
        select id, title, source_ai, priority, project_decision, decision_note
        from dev_proposals
        where source_ai='ceo_terminal_guard_bridge_v1'
        order by id desc
        limit 20
    """).fetchall()

    ranked = sorted([(score_row(r), r) for r in rows], reverse=True)

    selected_id = "none"

    if ranked and ranked[0][0] > 0 and (ranked[0][1]["project_decision"] or "") != "selected_now":
        selected = ranked[0][1]
        note = selected["decision_note"] or ""

        if "terminal_guard_selected" not in note:
            note = (note + " | terminal_guard_selected").strip(" |")

        c.execute("""
            update dev_proposals
            set project_decision='selected_now',
                priority=case
                    when coalesce(priority,0)=0
                     and (
                       coalesce(decision_note,'') like '%priority_fixed_85%'
                       or coalesce(decision_note,'') like '%terminal_executor_priority_fixed_85%'
                       or coalesce(decision_note,'') like '%terminal_guard_priority_synced%'
                     )
                    then 85
                    else coalesce(priority,0)
                end,
                decision_note=?
            where id=?
        """, (note, selected["id"]))

        con.commit()
        selected_id = selected["id"]

    path = "obs/runtime_generated/ceo_terminal_guard_selection.md"
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# CEO Terminal Guard Selection ({datetime.datetime.now()})\n")
        f.write(f"- selected_id: {selected_id}\n")

    print(f"ranked={len(ranked)}")

if __name__ == "__main__":
    main()
