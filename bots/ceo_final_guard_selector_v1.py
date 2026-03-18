from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/obs/runtime_generated/ceo_final_guard_selection.md")
SLEEP = 180

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def score_row(r):
    score = 0
    note = (r["decision_note"] or "")
    prio = int(r["priority"] or 0)
    score += prio
    if "final_executor_ready" in note:
        score += 20
    if "final_guard_from=" in note:
        score += 15
    if "priority_fixed_85" in note:
        score += 10
    if "selected_now" == (r["project_decision"] or ""):
        score -= 1000
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
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_final_executor_guarded_promoter_v1'
                order by id desc
                limit 20
            """).fetchall()

            ranked = []
            for r in rows:
                ranked.append((score_row(r), r))
            ranked.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)

            selected = None
            if ranked and ranked[0][0] > 0:
                selected = ranked[0][1]
                note = selected["decision_note"] or ""
                if "final_guard_selected" not in note:
                    note = (note + " | final_guard_selected").strip(" |")
                c.execute("""
                    update dev_proposals
                    set project_decision='selected_now',
                        priority=?,
                        decision_note=?
                    where id=?
                """, (max(int(selected["priority"] or 0), 85), note, selected["id"]))
                con.commit()

            lines = [f"# CEO Final Guard Selection ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"]
            if selected is None:
                lines += [
                    "- selected_id: none",
                    "| rank | score | id | source_ai | priority | title |",
                    "|---:|---:|---:|---|---:|---|",
                ]
            else:
                top_score = ranked[0][0]
                lines += [
                    f"- selected_id: {selected['id']}",
                    f"- selection_score: {top_score}",
                    f"- source_ai: {selected['source_ai']}",
                    f"- title: {selected['title']}",
                    f"- target_system: {selected['target_system']}",
                    f"- improvement_type: {selected['improvement_type']}",
                    f"- priority: {max(int(selected['priority'] or 0), 85)}",
                    f"- decision_note: {(selected['decision_note'] or '') + (' | final_guard_selected' if 'final_guard_selected' not in (selected['decision_note'] or '') else '')}",
                    f"- created_at: {selected['created_at']}",
                    "| rank | score | id | source_ai | priority | title |",
                    "|---:|---:|---:|---|---:|---|",
                ]
                for i, (sc, r) in enumerate(ranked, 1):
                    lines.append(f"| {i} | {sc} | {r['id']} | {r['source_ai']} | {max(int(r['priority'] or 0), 85) if r['id']==selected['id'] else int(r['priority'] or 0)} | {r['title']} |")

            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

            con.close()
            print(f"{datetime.now().isoformat()} ranked={len(ranked)}", flush=True)
        except Exception as e:
            print(f"ceo_final_guard_selector_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
