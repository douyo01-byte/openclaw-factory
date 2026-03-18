from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/obs/runtime_generated/ceo_execution_selection.md")
SLEEP = 300

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def pick(rows):
    best = None
    best_score = None
    for r in rows:
        score = int(r["priority"] or 0)
        target = r["target_system"] or ""
        imp = r["improvement_type"] or ""
        title = r["title"] or ""

        if target in ("ceo_decision_layer_v1", "ceo_interface", "web_dashboard"):
            score += 20
        if imp in ("autonomous_planning", "human_interface", "ui_platform"):
            score += 10
        if "web" in title.lower():
            score += 10

        if best is None or score > best_score or (score == best_score and r["id"] > best["id"]):
            best = r
            best_score = score

    return best, best_score

def render(best, score):
    lines = []
    lines.append(f"# CEO Execution Selection ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    if not best:
        lines.append("")
        lines.append("No promoted execution candidate found.")
        return "\n".join(lines) + "\n"

    lines.append("")
    lines.append(f"- selected_id: {best['id']}")
    lines.append(f"- selection_score: {score}")
    lines.append(f"- title: {best['title'] or ''}")
    lines.append(f"- target_system: {best['target_system'] or ''}")
    lines.append(f"- improvement_type: {best['improvement_type'] or ''}")
    lines.append(f"- priority: {int(best['priority'] or 0)}")
    lines.append(f"- decision_note: {best['decision_note'] or ''}")
    lines.append(f"- created_at: {best['created_at'] or ''}")
    return "\n".join(lines) + "\n"

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()

            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(priority,0) as priority,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_growth_promoter_v1'
                order by id desc
                limit 50
            """).fetchall()

            best, score = pick(rows)

            if best:
                c.execute("""
                    update dev_proposals
                    set project_decision='selected_now',
                        decision_note=trim(coalesce(decision_note,'') || ' | selected_for_execution')
                    where id=?
                      and coalesce(source_ai,'')='ceo_growth_promoter_v1'
                      and coalesce(decision_note,'') not like '%selected_for_execution%';
                """, (best["id"],))

            con.commit()
            con.close()

            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(render(best, score), encoding="utf-8")
            print(f"{datetime.now().isoformat()} selected={(best['id'] if best else 0)}", flush=True)
        except Exception as e:
            print(f"execution_selector_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
