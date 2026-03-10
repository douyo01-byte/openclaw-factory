from __future__ import annotations
import os
import sqlite3
from datetime import datetime, UTC

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"

def one(conn, q):
    r = conn.execute(q).fetchone()
    return 0 if not r else int(r[0] or 0)

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    conn.execute("""
    create table if not exists ceo_hub_events(
      id integer primary key,
      event_type text,
      title text,
      body text,
      proposal_id integer,
      pr_url text,
      created_at text default (datetime('now')),
      sent_at text
    )
    """)

    queue = one(conn, """
    select count(*)
    from dev_proposals
    where status='approved'
      and coalesce(project_decision,'')='execute_now'
      and coalesce(guard_status,'')='safe'
    """)

    open_pr = one(conn, """
    select count(*)
    from dev_proposals
    where coalesce(status,'')='open'
       or coalesce(pr_status,'')='open'
       or coalesce(dev_stage,'')='open'
    """)

    flow = "proposal_flow_ok"
    if open_pr > 5:
        flow = "open_pr_high"
    elif queue > 20:
        flow = "queue_high"

    body = f"queue={queue}\nopen_pr={open_pr}\nflow={flow}"
    conn.execute("""
    insert into ceo_hub_events(event_type, title, body, proposal_id, pr_url, created_at)
    values('executor_audit', 'executor audit', ?, null, '', ?)
    """, (body, datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    print("[executor_audit]")
    print(flow)
    print(f"queue={queue}")
    print(f"open_pr={open_pr}")

if __name__ == "__main__":
    main()
