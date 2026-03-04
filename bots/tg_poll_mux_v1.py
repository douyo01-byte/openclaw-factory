import os, json, time, sqlite3, urllib.parse, urllib.request

DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
TOKEN=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
BASE=f"https://api.telegram.org/bot{TOKEN}"

def _conn():
    return sqlite3.connect(DB_PATH, timeout=30)

def _init_db():
    con=_conn()
    con.execute("""
create table if not exists tg_private_ingest_state(
  id integer primary key,
  last_update_id integer
)
""")
    con.execute("""
create table if not exists tg_private_chat_log(
  id integer primary key autoincrement,
  message_id integer,
  text text,
  created_at datetime default current_timestamp
)
""")
    con.execute("""
create table if not exists inbox_commands(
  id integer primary key autoincrement,
  chat_id text,
  message_id integer,
  reply_to_message_id integer,
  from_username text,
  from_name text,
  text text,
  received_at datetime default current_timestamp,
  applied_at datetime,
  status text,
  error text,
  processed integer default 0
)
""")
    con.commit()
    con.close()

def _get_offset(con):
    row=con.execute("select last_update_id from tg_private_ingest_state where id=1").fetchone()
    return int(row[0]) if row and row[0] is not None else 0

def _set_offset(con, off):
    con.execute("insert into tg_private_ingest_state(id,last_update_id) values(1,?) on conflict(id) do update set last_update_id=excluded.last_update_id",(int(off),))

def call_getupdates(offset, timeout=25):
    params={
        "timeout": str(int(timeout)),
        "offset": str(int(offset)),
        "allowed_updates": json.dumps(["message"]),
    }
    qs=urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{BASE}/getUpdates?{qs}", timeout=timeout+10) as r:
        return json.loads(r.read().decode("utf-8","replace"))

def upsert_private(con, msg):
    mid=msg.get("message_id")
    text=msg.get("text") or ""
    if mid is None:
        return
    con.execute("insert into tg_private_chat_log(message_id,text) values(?,?)",(int(mid),str(text)))

def upsert_inbox(con, msg):
    chat=msg.get("chat") or {}
    frm=msg.get("from") or {}
    mid=msg.get("message_id")
    if mid is None:
        return
    chat_id=str(chat.get("id"))
    reply_to=msg.get("reply_to_message") or {}
    reply_mid=reply_to.get("message_id")
    from_username=frm.get("username")
    from_name=(" ".join([x for x in [frm.get("first_name"),frm.get("last_name")] if x]) or None)
    text=msg.get("text") or ""
    con.execute("""
insert into inbox_commands(chat_id,message_id,reply_to_message_id,from_username,from_name,text,status,processed)
values(?,?,?,?,?,?,?,?)
""",(chat_id,int(mid),int(reply_mid) if reply_mid is not None else None,from_username,from_name,str(text),"received",0))

def main():
    if not TOKEN:
        raise SystemExit("missing TELEGRAM_BOT_TOKEN")
    _init_db()
    while True:
        con=_conn()
        try:
            offset=_get_offset(con)
            data=call_getupdates(offset, timeout=25)
            res=data.get("result") or []
            if not res:
                con.close()
                continue
            for upd in res:
                uid=upd.get("update_id")
                msg=upd.get("message") or {}
                chat=(msg.get("chat") or {})
                ctype=chat.get("type") or ""
                if uid is None:
                    continue
                nxt=int(uid)+1
                if ctype=="private":
                    upsert_private(con,msg)
                else:
                    upsert_inbox(con,msg)
                _set_offset(con,nxt)
                offset=nxt
            con.commit()
        except Exception as e:
            try:
                con.rollback()
            except Exception:
                pass
            print("ERR:",repr(e),flush=True)
            time.sleep(1)
        finally:
            try:
                con.close()
            except Exception:
                pass

if __name__=="__main__":
    main()
