from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("/Users/doyopc/AI/openclaw-factory-daemon/reports/audit_20260317/ceo_mainline_lane_digest.md")
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
                  coalesce(status,'') as status,
                  coalesce(source_ai,'') as source_ai,
                  coalesce(target_system,'') as target_system,
                  coalesce(improvement_type,'') as improvement_type,
                  coalesce(title,'') as title,
                  coalesce(decision_note,'') as decision_note,
                  coalesce(created_at,'') as created_at
                from dev_proposals
                where coalesce(source_ai,'') in ('ceo_mainline_promoter_v1','ceo_execution_bridge_v1')
                order by cast(coalesce(priority,0) as integer) desc, id desc
                limit 30
            """).fetchall()
            con.close()

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lines = [f"# CEO Mainline Lane Digest ({ts})"]
            lines.append("| id | priority | status | decision | source_ai | target_system | improvement_type | title | note | created_at |")
            lines.append("|---:|---:|---|---|---|---|---|---|---|---|")
            for r in rows:
                note = (r["decision_note"] or "").replace("|", "/").replace("\n", " ")
                title = (r["title"] or "").replace("\n", " ")
                lines.append(
                    f"| {r['id']} | {int(r['priority'])} | {r['status']} | {r['project_decision']} | "
                    f"{r['source_ai']} | {r['target_system']} | {r['improvement_type']} | "
                    f"{title} | {note} | {r['created_at']} |"
                )
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"{datetime.now().isoformat()} digest_written={len(rows)}", flush=True)
        except Exception as e:
            print(f"mainline_lane_digest_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
