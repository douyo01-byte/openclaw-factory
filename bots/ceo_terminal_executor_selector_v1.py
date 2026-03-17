from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/reports/audit_20260317/ceo_terminal_executor_selection.md")
SLEEP = 120

def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def score_row(r):
    note = (r["decision_note"] or "")
    score = 0
    p = int(r["priority"] or 0)
    score += p
    if "terminal_executor_ready" in note:
        score += 30
    if "terminal_executor_priority_synced" in note:
        score += 10
    if "final_guard_row_selected" in note:
        score += 5
    if "selected_now" == (r["project_decision"] or ""):
        score -= 100
    return score

def write_report(rows, selected):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# CEO Terminal Executor Selection ({ts})"]
    if selected:
        lines += [
            f"- selected_id: {selected['id']}",
            f"- selection_score: {selected['score']}",
            f"- source_ai: {selected['source_ai']}",
            f"- title: {selected['title']}",
            f"- target_system: {selected['target_system']}",
            f"- improvement_type: {selected['improvement_type']}",
            f"- priority: {selected['priority']}",
            f"- decision_note: {selected['decision_note']}",
            f"- created_at: {selected['created_at']}",
        ]
    else:
        lines += ["- selected_id: none"]
    lines += [
        "| rank | score | id | source_ai | priority | title |",
        "|---:|---:|---:|---|---:|---|",
    ]
    for i, r in enumerate(rows, 1):
        title = (r["title"] or "").replace("\n", " ").replace("|", "/")
        lines.append(f"| {i} | {r['score']} | {r['id']} | {r['source_ai']} | {r['priority']} | {title} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    while True:
        try:
            con = connect()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  title,
                  source_ai,
                  coalesce(priority,0) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_terminal_executor_bridge_v1'
                order by id desc
                limit 20
            """).fetchall()

            ranked = []
            for r in rows:
                d = dict(r)
                d["score"] = score_row(r)
                ranked.append(d)
            ranked.sort(key=lambda x: (-x["score"], -x["id"]))

            selected = None
            for r in ranked:
                note = r["decision_note"] or ""
                if "terminal_executor_ready" not in note:
                    continue
                if "terminal_executor_selected" in note:
                    continue
                if int(r["priority"] or 0) < 85:
                    continue
                selected = r
                break

            if selected:
                note = selected["decision_note"]
                note = (note + " | terminal_executor_selected").strip(" |")
                c.execute("""
                    update dev_proposals
                    set
                      project_decision='selected_now',
                      decision_note=?
                    where id=?
                """, (note, selected["id"]))
                con.commit()
                selected["project_decision"] = "selected_now"
                selected["decision_note"] = note

            write_report(ranked, selected)
            con.close()
            print(f"{datetime.now().isoformat()} ranked={len(ranked)}", flush=True)
        except Exception as e:
            print(f"ceo_terminal_executor_selector_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
