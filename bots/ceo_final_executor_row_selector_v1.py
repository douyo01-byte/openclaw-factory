from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 180
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/obs/runtime_generated/ceo_final_executor_row_selection.md")

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def score_row(r):
    note = r["decision_note"] or ""
    score = int(r["priority"] or 0)
    if "final_executor_row_priority_synced" in note:
        score += 20
    if "priority_fixed_85" in note:
        score += 10
    if "guard_executor_ready" in note:
        score += 10
    if "final_executor_selected" in note:
        score += 10
    return score

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(source_ai,'') as source_ai,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_executor_bridge_v1'
                  and coalesce(status,'')='new'
                order by id desc
                limit 20
            """).fetchall()

            ranked = sorted(((score_row(r), r) for r in rows), key=lambda x: (-x[0], -int(x[1]["id"])))
            selected = ranked[0][1] if ranked else None
            selected_score = ranked[0][0] if ranked else 0

            OUT.parent.mkdir(parents=True, exist_ok=True)
            lines = [f"# CEO Final Executor Row Selection ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"]
            if selected:
                lines += [
                    f"- selected_id: {selected['id']}",
                    f"- selection_score: {selected_score}",
                    f"- source_ai: {selected['source_ai']}",
                    f"- title: {selected['title']}",
                    f"- target_system: {selected['target_system']}",
                    f"- improvement_type: {selected['improvement_type']}",
                    f"- priority: {int(selected['priority'] or 0)}",
                    f"- decision_note: {selected['decision_note']}",
                    f"- created_at: {selected['created_at']}",
                ]
            else:
                lines += ["- selected_id: none"]

            lines += ["| rank | score | id | source_ai | priority | title |", "|---:|---:|---:|---|---:|---|"]
            for i, (s, r) in enumerate(ranked, 1):
                lines.append(f"| {i} | {s} | {r['id']} | {r['source_ai']} | {int(r['priority'] or 0)} | {r['title']} |")
            OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

            if selected:
                note = selected["decision_note"] or ""
                if "final_executor_row_selected" not in note:
                    note = (note + " | final_executor_row_selected").strip(" |")
                if "final_executor_row_priority_synced" not in note:
                    note = (note + " | final_executor_row_priority_synced").strip(" |")
                c.execute("""
                    update dev_proposals
                    set project_decision='selected_now',
                        priority=case
                          when cast(coalesce(priority,0) as integer) < 85 then 85
                          else cast(coalesce(priority,0) as integer)
                        end,
                        decision_note=?
                    where id=?
                """, (note, selected["id"]))
                con.commit()

            con.close()
            print(f"{datetime.now().isoformat()} ranked={len(ranked)}", flush=True)
        except Exception as e:
            print(f"final_executor_row_selector_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
