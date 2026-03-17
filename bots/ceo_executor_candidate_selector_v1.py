from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/reports/audit_20260317/ceo_executor_candidate_selection.md")
SLEEP = 300

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def effective_priority(row):
    note = row["decision_note"] or ""
    base = int(row["priority"] or 0)
    if "priority_fixed_85" in note:
        base = max(base, 85)
    if "executor_ready" in note:
        base += 20
    if "selected_for_execution" in note:
        base += 20
    if "bridged_to_mainline" in note:
        base += 10
    if row["source_ai"] == "ceo_mainline_promoter_v1":
        base += 10
    return base

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
                  coalesce(status,'') as status,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(status,'')='new'
                  and (
                    coalesce(source_ai,'')='ceo_mainline_promoter_v1'
                    or coalesce(source_ai,'')='ceo_execution_bridge_v1'
                    or (
                      coalesce(project_decision,'')='go'
                      and coalesce(dev_stage,'')=''
                      and coalesce(pr_status,'')=''
                    )
                  )
                order by id desc
                limit 200
            """).fetchall()
            con.close()

            ranked = []
            for r in rows:
                score = effective_priority(r)
                ranked.append((score, r))
            ranked.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lines = [f"# CEO Executor Candidate Selection ({ts})"]
            if ranked:
                best_score, best = ranked[0]
                lines.append(f"- selected_id: {best['id']}")
                lines.append(f"- selection_score: {best_score}")
                lines.append(f"- source_ai: {best['source_ai']}")
                lines.append(f"- title: {best['title']}")
                lines.append(f"- target_system: {best['target_system']}")
                lines.append(f"- improvement_type: {best['improvement_type']}")
                lines.append(f"- priority: {int(best['priority'] or 0)}")
                lines.append(f"- decision_note: {best['decision_note']}")
                lines.append(f"- created_at: {best['created_at']}")
                lines.append("")
                lines.append("| rank | score | id | source_ai | priority | title |")
                lines.append("|---:|---:|---:|---|---:|---|")
                for i, (score, r) in enumerate(ranked[:10], start=1):
                    title = (r["title"] or "").replace("\n", " ")
                    lines.append(f"| {i} | {score} | {r['id']} | {r['source_ai']} | {int(r['priority'] or 0)} | {title} |")
            else:
                lines.append("- selected_id: none")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"{datetime.now().isoformat()} ranked={len(ranked)}", flush=True)
        except Exception as e:
            print(f"executor_candidate_selector_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
