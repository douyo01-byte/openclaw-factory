import os
import re
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^a-z0-9ぁ-んァ-ヶ一-龠_-]", "", s)
    return s[:160]

def run_once():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        select id, coalesce(title,'') as title, coalesce(source_ai,'') as source_ai,
               coalesce(status,'') as status, coalesce(project_decision,'') as project_decision,
               created_at
        from dev_proposals
        where coalesce(status,'') in ('new','approved','pending','idea')
        order by id desc
        limit 1000
    """).fetchall()

    seen = {}
    closed = 0
    for r in rows:
        key = norm(r["title"])
        if not key:
            continue
        if key not in seen:
            seen[key] = r["id"]
            continue
        keep_id = max(seen[key], r["id"])
        drop_id = min(seen[key], r["id"])
        con.execute("""
            update dev_proposals
            set status='closed',
                dev_stage='closed',
                result_note='deduped'
            where id=?
              and coalesce(status,'') not in ('merged','closed')
        """, (drop_id,))
        seen[key] = keep_id
        closed += con.total_changes > 0

    con.commit()
    con.close()
    print(f"proposal_dedupe_closed={int(closed)}", flush=True)

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(120)
