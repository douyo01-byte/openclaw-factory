import os
import re
import time
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or os.path.expanduser("/Users/doyopc/AI/openclaw-factory-daemon/data/openclaw_real.db")

def connect():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("""
    create table if not exists kv(
      k text primary key,
      v text not null,
      updated_at text default (datetime('now'))
    )
    """)
    return conn

def kv_get(conn, k):
    r = conn.execute("select v from kv where k=?", (k,)).fetchone()
    return r[0] if r else None

def kv_set(conn, k, v):
    for _ in range(10):
        try:
            conn.execute("""
            insert into kv(k,v,updated_at) values(?,?,datetime('now'))
            on conflict(k) do update set v=excluded.v, updated_at=datetime('now')
            """, (k, str(v)))
            return
        except sqlite3.OperationalError as e:
            if "locked" not in str(e).lower():
                raise
            time.sleep(0.5)
    conn.execute("""
    insert into kv(k,v,updated_at) values(?,?,datetime('now'))
    on conflict(k) do update set v=excluded.v, updated_at=datetime('now')
    """, (k, str(v)))

def parse_reply(text):
    t = (text or "").strip()
    m = re.match(r"^#?(\d+)\s+(.+)$", t, re.S)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, None

def run():
    conn = connect()
    offset = int(kv_get(conn, "spec_reply_offset") or "0")
    rows = conn.execute("""
    select id, coalesce(text,'') as text
    from inbox_commands
    where id > ?
    order by id asc
    limit 200
    """, (offset,)).fetchall()

    done = 0
    for r in rows:
        offset = int(r["id"])
        pid, body = parse_reply(r["text"])
        if pid and body:
            conn.execute("""
            insert into proposal_conversation(proposal_id, role, message, created_at)
            values(?,?,?,datetime('now'))
            """, (pid, "user", body))
            conn.execute("""
            insert into proposal_state(proposal_id, stage, updated_at)
            values(?, 'answer_received', datetime('now'))
            on conflict(proposal_id) do update set
              stage='answer_received',
              updated_at=datetime('now')
            """, (pid,))
            conn.execute("""
            update dev_proposals
            set spec_stage='answer_received'
            where id=?
            """, (pid,))
            done += 1
        kv_set(conn, "spec_reply_offset", offset)

    conn.commit()
    conn.close()
    print(f"spec_reply_done={done} last_id={offset}")

if __name__ == "__main__":
    run()
