from __future__ import annotations
import os
import time
import sqlite3
from pathlib import Path
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/reports/audit_20260317/ceo_problem_digest.md")
SLEEP = 300

def main():
    while True:
        try:
            con = sqlite3.connect(DB, timeout=30)
            con.row_factory = sqlite3.Row
            con.execute("pragma busy_timeout=30000")
            c = con.cursor()

            rows = c.execute("""
                select
                  id,
                  coalesce(title,'') as title,
                  coalesce(source_ai,'') as source_ai,
                  coalesce(status,'') as status,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_problem_detector_v1'
                order by priority desc, id desc
                limit 30
            """).fetchall()

            lines = []
            lines.append(f"# CEO Problem Digest ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            lines.append("")
            lines.append("| id | priority | decision | target_system | improvement_type | title | note | created_at |")
            lines.append("|---:|---:|---|---|---|---|---|---|")
            for r in rows:
                title = r["title"].replace("|", "/")
                note = r["decision_note"].replace("|", "/")
                prio = int(r["priority"]) if r["priority"] is not None else 0
                lines.append(
                    f"| {r['id']} | {prio} | {r['project_decision']} | {r['target_system']} | {r['improvement_type']} | {title} | {note} | {r['created_at']} |"
                )

            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
            con.close()
            print(f"{datetime.now().isoformat()} digest_written={len(rows)}", flush=True)

        except Exception as e:
            print(f"digest_error: {e}", flush=True)

        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
