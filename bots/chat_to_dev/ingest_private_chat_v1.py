import os
import sqlite3

DB=os.environ.get("DB_PATH","data/openclaw.db")

def ensure(conn):
    conn.execute("create table if not exists tg_kv(k text primary key, v text)")
    conn.execute("""
    create table if not exists inbox_commands(
      id integer primary key autoincrement,
      chat_id integer,
      text text,
      status text,
      processed integer default 0,
      created_at text default (datetime('now')),
      applied_at text,
      error text
    )
    """)
    conn.execute("""
    create table if not exists tg_private_chat_log(
      id integer primary key autoincrement,
      update_id integer unique,
      message_id integer,
      chat_id integer,
      text text,
      created_at text default (datetime('now'))
    )
    """)
    cols={r[1] for r in conn.execute("pragma table_info(tg_private_chat_log)")}
    if "chat_id" not in cols:
        conn.execute("alter table tg_private_chat_log add column chat_id integer")
    cols={r[1] for r in conn.execute("pragma table_info(inbox_commands)")}
    if "chat_id" not in cols:
        conn.execute("alter table inbox_commands add column chat_id integer")

def kv_get(conn,k):
    r=conn.execute("select v from tg_kv where k=?", (k,)).fetchone()
    return r[0] if r else None

def kv_set(conn,k,v):
    conn.execute(
        "insert into tg_kv(k,v) values(?,?) on conflict(k) do update set v=excluded.v",
        (k,str(v))
    )

def main():
    conn=sqlite3.connect(DB, timeout=30)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    ensure(conn)

    last_id=int(kv_get(conn,"tg_private_chat_last_id") or 0)

    rows=conn.execute("""
        select id, chat_id, trim(coalesce(text,'')) as text
        from tg_private_chat_log
        where id > ?
        order by id asc
        limit 100
    """,(last_id,)).fetchall()

    queued=0
    max_id=last_id

    for r in rows:
        rid=int(r["id"])
        chat_id=r["chat_id"]
        text=(r["text"] or "").strip()
        if rid > max_id:
            max_id=rid
        if not text:
            continue

        exists=conn.execute("""
            select 1
            from inbox_commands
            where chat_id=?
              and text=?
              and created_at > datetime('now','-30 minutes')
            limit 1
        """,(chat_id,text)).fetchone()

        if not exists:
            conn.execute("""
                insert into inbox_commands(chat_id,text,status,processed,created_at)
                values(?,?,?,0,datetime('now'))
            """,(chat_id,text,"pending"))
            queued+=1

    kv_set(conn,"tg_private_chat_last_id",max_id)
    conn.commit()
    conn.close()
    print(f"queued={queued} last_id={max_id}", flush=True)

if __name__=="__main__":
    main()
