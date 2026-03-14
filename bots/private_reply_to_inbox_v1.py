from __future__ import annotations
import os, time, sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("PRIVATE_REPLY_TO_INBOX_SLEEP", "5"))

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(tg_private_chat_log)").fetchall()}
    if "router_ingested" not in cols:
        c.execute("alter table tg_private_chat_log add column router_ingested text default ''")
    if "router_ingested_at" not in cols:
        c.execute("alter table tg_private_chat_log add column router_ingested_at text default ''")

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
        select id, coalesce(message_id,0) as message_id, coalesce(chat_id,'') as chat_id, coalesce(text,'') as text
        from tg_private_chat_log
        where coalesce(router_ingested,'')=''
          and coalesce(text,'')<>''
        order by id asc
        limit 20
        """).fetchall()
        done = 0
        for r in rows:
            c.execute("""
            insert into inbox_commands(
              source, text, status, processed, chat_id, message_id, created_at, updated_at, router_finish_status
            ) values (
              'private_reply_bridge',
              ?, 'pending', 1, ?, ?, datetime('now'), datetime('now'), ''
            )
            """, (r["text"], str(r["chat_id"]), int(r["message_id"])))
            c.execute("""
            update tg_private_chat_log
            set router_ingested='yes',
                router_ingested_at=datetime('now')
            where id=?
            """, (r["id"],))
            done += 1
        if done:
            c.commit()
        print(f"[private_reply_to_inbox_v1] done={done}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[private_reply_to_inbox_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
