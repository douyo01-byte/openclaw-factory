import os
import sqlite3
import requests

DB=os.environ.get("DB_PATH","data/openclaw.db")
TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]

def ensure(conn):
    conn.execute("create table if not exists tg_kv(k text primary key, v text)")
    conn.execute("""
    create table if not exists tg_private_chat_log(
      id integer primary key autoincrement,
      update_id integer unique,
      message_id integer,
      text text,
      created_at text default (datetime('now'))
    )
    """)
    cols={r[1] for r in conn.execute("pragma table_info(tg_private_chat_log)")}
    if "update_id" not in cols:
        conn.execute("alter table tg_private_chat_log add column update_id integer")
    if "created_at" not in cols:
        conn.execute("alter table tg_private_chat_log add column created_at text")

def kv_get(conn,k):
    r=conn.execute("select v from tg_kv where k=?", (k,)).fetchone()
    return r[0] if r else None

def kv_set(conn,k,v):
    conn.execute(
        "insert into tg_kv(k,v) values(?,?) on conflict(k) do update set v=excluded.v",
        (k,str(v))
    )

def main():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    ensure(conn)

    offset=kv_get(conn,"tg_private_update_offset")
    params={"timeout":0}
    if offset is not None:
        params["offset"]=int(offset)+1

    r=requests.get(
        f"https://api.telegram.org/bot{TOKEN}/getUpdates",
        params=params,
        timeout=60
    )
    r.raise_for_status()
    data=r.json()

    seen=0
    last_uid=None
    for u in data.get("result",[]):
        uid=u.get("update_id")
        m=u.get("message")
        if uid is None:
            continue
        last_uid=uid
        if not m:
            continue
        if m.get("chat",{}).get("type")!="private":
            continue

        mid=m.get("message_id")
        text=m.get("text","")
        conn.execute(
            "insert or ignore into tg_private_chat_log(update_id,message_id,text,created_at) values(?,?,?,datetime('now'))",
            (uid,mid,text)
        )
        seen+=1

    if last_uid is not None:
        kv_set(conn,"tg_private_update_offset",last_uid)

    conn.commit()
    conn.close()
    print(f"seen={seen}", flush=True)

if __name__=="__main__":
    main()
