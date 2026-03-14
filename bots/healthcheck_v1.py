import os
import sqlite3
from datetime import datetime

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def one(conn, sql):
    row = conn.execute(sql).fetchone()
    return row[0] if row else None

def upsert_event(conn, title: str, body: str):
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
    last = conn.execute("""
        select id, coalesce(body,'')
        from ceo_hub_events
        where coalesce(event_type,'')='healthcheck'
        order by id desc
        limit 1
    """).fetchone()
    if last and (last[1] or "").strip() == body.strip():
        return
    conn.execute("""
        insert into ceo_hub_events(event_type,title,body,created_at)
        values('healthcheck', ?, ?, datetime('now'))
    """, (title, body))
    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("pragma busy_timeout=30000")
    try:
        parts = [
            "🟢 OpenClaw Alive",
            f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        try:
            items = one(conn, "select count(*) from items")
        except Exception:
            items = "n/a"
        try:
            contacts = one(conn, "select count(*) from contacts")
        except Exception:
            contacts = "n/a"
        try:
            commands = one(conn, "select count(*) from inbox_commands")
        except Exception:
            commands = "n/a"
        try:
            open_pr = one(conn, "select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
        except Exception:
            open_pr = "n/a"
        try:
            approved = one(conn, "select count(*) from dev_proposals where coalesce(status,'')='approved'")
        except Exception:
            approved = "n/a"

        parts.append(f"items: {items}")
        parts.append(f"contacts: {contacts}")
        parts.append(f"commands: {commands}")
        parts.append(f"open_pr: {open_pr}")
        parts.append(f"approved: {approved}")
        parts.append("status: OK")

        body = "\n".join(parts)
        upsert_event(conn, "healthcheck", body)
        print("[healthcheck] ceo_hub_events updated", flush=True)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
