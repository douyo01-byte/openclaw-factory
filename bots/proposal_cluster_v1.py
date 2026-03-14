import os
import re
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def normalize_title(title: str) -> str:
    t = (title or "").lower().strip()
    t = re.sub(r'[^a-z0-9ぁ-んァ-ヶ一-龠]+', ' ', t)
    words = [w for w in t.split() if len(w) >= 2]
    stop = {
        "improve","reduce","add","fix","update","refactor","strengthen",
        "normalize","introduce","ensure","coverage","latency","drift",
        "mothership","proposal","openclaw"
    }
    words = [w for w in words if w not in stop]
    if not words:
        return "misc"
    return "_".join(words[:3])

def run_once():
    c = conn()
    try:
        rows = c.execute("""
            select
              id,
              coalesce(title,'') as title,
              coalesce(status,'') as status,
              coalesce(source_ai,'') as source_ai
            from dev_proposals
            where coalesce(status,'') not in ('merged','closed')
            order by id desc
            limit 500
        """).fetchall()

        inserted = 0
        for r in rows:
            key = normalize_title(r["title"])
            c.execute("""
                insert or ignore into proposal_clusters(
                  cluster_key,
                  proposal_id,
                  title,
                  status,
                  source_ai,
                  created_at
                ) values(?,?,?,?,?,datetime('now'))
            """, (
                key,
                int(r["id"]),
                str(r["title"] or ""),
                str(r["status"] or ""),
                str(r["source_ai"] or ""),
            ))
            if c.total_changes > 0:
                inserted += 1

        c.commit()
        print(f"proposal_cluster_inserted={inserted}", flush=True)
    finally:
        c.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(180)
