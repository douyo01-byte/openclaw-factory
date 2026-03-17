from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/reports/audit_20260317/ceo_executor_lane_digest.md")
SLEEP = 300

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def main():
    while True:
        try:
            con = conn()
            c = con.cursor()
            rows = c.execute("""
                select
                  id,
                  cast(coalesce(priority,0) as integer) as priority,
                  coalesce(project_decision,'') as project_decision,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(title,'') as title,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'')='ceo_mainline_promoter_v1'
                  and coalesce(status,'')='new'
                  and coalesce(decision_note,'') like '%executor_ready%'
                order by coalesce(priority,0) desc, id desc
                limit 20
            """).fetchall()
            con.close()

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lines = [f"# CEO Executor Lane Digest ({ts})"]
            lines.append("| id | priority | decision | target_system | improvement_type | title | note | created_at |")
            lines.append("|---:|---:|---|---|---|---|---|---|")
            for r in rows:
                note = (r["decision_note"] or "").replace("|", "/")
                title = (r["title"] or "").replace("\n", " ")
                lines.append(
                    f"| {r['id']} | {int(r['priority'])} | {r['project_decision']} | "
                    f"{r['target_system']} | {r['improvement_type']} | {title} | {note} | {r['created_at']} |"
                )
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"{datetime.now().isoformat()} digest_written={len(rows)}", flush=True)
        except Exception as e:
            print(f"executor_lane_digest_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
