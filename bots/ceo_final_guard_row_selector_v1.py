from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/obs/runtime_generated/ceo_final_guard_row_selection.md")
SLEEP = 120

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def score(row):
    s = 0
    note = row["decision_note"] or ""
    prio = int(row["priority"] or 0)
    s += prio
    if "final_guard_ready" in note:
        s += 30
    if "final_executor_ready" in note:
        s += 20
    if "priority_fixed_85" in note:
        s += 10
    return s

def render(rows, selected):
    lines = []
    lines.append(f"# CEO Final Guard Row Selection ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    if selected:
        lines.append(f"- selected_id: {selected['id']}")
        lines.append(f"- selection_score: {selected['score']}")
        lines.append(f"- source_ai: {selected['source_ai']}")
        lines.append(f"- title: {selected['title']}")
        lines.append(f"- target_system: {selected['target_system']}")
        lines.append(f"- improvement_type: {selected['improvement_type']}")
        lines.append(f"- priority: {selected['priority']}")
        lines.append(f"- decision_note: {selected['decision_note']}")
        lines.append(f"- created_at: {selected['created_at']}")
    else:
        lines.append("- selected_id: none")
    lines.append("| rank | score | id | source_ai | priority | title |")
    lines.append("|---:|---:|---:|---|---:|---|")
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r['score']} | {r['id']} | {r['source_ai']} | {r['priority']} | {r['title']} |")
    return "\n".join(lines) + "\n"

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            con = conn()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(source_ai,'') as source_ai,
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_guard_bridge_v1'
                  and coalesce(status,'')='new'
                order by id desc
                limit 20
            """).fetchall()

            ranked = []
            for r in rows:
                rr = dict(r)
                rr["score"] = score(r)
                ranked.append(rr)
            ranked.sort(key=lambda x: (x["score"], x["id"]), reverse=True)

            selected = None
            for r in ranked:
                note = r["decision_note"] or ""
                if "final_guard_ready" in note and "final_guard_row_selected" not in note:
                    selected = r
                    break

            if selected:
                note = selected["decision_note"] or ""
                if "final_guard_row_selected" not in note:
                    note = (note + " | final_guard_row_selected").strip(" |")
                c.execute("""
                    update dev_proposals
                    set project_decision='selected_now',
                        decision_note=?
                    where id=?
                """, (note, selected["id"]))
                selected["decision_note"] = note

            OUT.write_text(render(ranked, selected), encoding="utf-8")
            con.commit()
            con.close()
            print(f"{datetime.now().isoformat()} ranked={len(ranked)}", flush=True)
        except Exception as e:
            print(f"ceo_final_guard_row_selector_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
