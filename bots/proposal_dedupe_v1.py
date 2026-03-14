import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def norm(t: str) -> str:
    return "".join((t or "").lower().split())

def run_once():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=30000")
    rows = conn.execute("""
        select id, coalesce(title,'') as title, coalesce(source_ai,'') as source_ai,
               coalesce(status,'') as status, created_at
        from dev_proposals
        where coalesce(status,'') in ('approved','new','pending','idea')
        order by id desc
        limit 1000
    """).fetchall()

    seen = {}
    closed = []
    for r in rows:
        k = (norm(r["title"]), (r["source_ai"] or "").strip().lower())
        if not k[0]:
            continue
        if k not in seen:
            seen[k] = r["id"]
            continue
        newer = seen[k]
        older = r["id"]
        conn.execute("""
            update dev_proposals
            set status='closed',
                dev_stage=case when coalesce(dev_stage,'')='' then 'closed' else dev_stage end,
                pr_status=case when coalesce(pr_status,'')='' then 'closed' else pr_status end,
                decision_note=trim(coalesce(decision_note,'') || ' deduped_by_proposal_dedupe_v1')
            where id=?
              and coalesce(status,'') in ('approved','new','pending','idea')
              and coalesce(dev_stage,'') not in ('merged')
        """, (older,))
        closed.append((older, newer, r["title"]))

    conn.commit()
    conn.close()
    print(f"proposal_dedupe_closed={len(closed)}", flush=True)
    for older, newer, title in closed[:20]:
        print(f"[proposal_dedupe] closed old={older} keep={newer} title={title}", flush=True)

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(300)
