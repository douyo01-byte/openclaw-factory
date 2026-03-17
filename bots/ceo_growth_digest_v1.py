from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/reports/audit_20260317/ceo_growth_digest.md")
SLEEP = 300

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def render(rows):
    lines = []
    lines.append(f"# CEO Growth Digest ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    lines.append("| id | priority | decision | target_system | improvement_type | title | note | created_at |")
    lines.append("|---:|---:|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['id']} | {int(r['priority'] or 0)} | {r['project_decision'] or ''} | "
            f"{r['target_system'] or ''} | {r['improvement_type'] or ''} | "
            f"{(r['title'] or '').replace('|','/')} | {(r['decision_note'] or '').replace('|','/')} | "
            f"{r['created_at'] or ''} |"
        )
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
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_growth_planner_v1'
                order by priority desc, id desc
                limit 20
            """).fetchall()
            con.close()
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(render(rows), encoding="utf-8")
            print(f"{datetime.now().isoformat()} digest_written={len(rows)}", flush=True)
        except Exception as e:
            print(f"growth_digest_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
