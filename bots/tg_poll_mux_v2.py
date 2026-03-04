import os,sys,time,json,sqlite3,urllib.parse,urllib.request,urllib.error,datetime,fcntl
DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
TOKEN=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
BASE=f"https://api.telegram.org/bot{TOKEN}"
POLL_TIMEOUT=int(os.environ.get("TG_POLL_TIMEOUT") or "25")
LOCK_PATH=os.environ.get("OCLAW_TG_POLL_LOCK") or "/tmp/jp.openclaw.tg_poll_mux_v2.lock"
def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def call_getupdates(offset:int):
    qs=urllib.parse.urlencode({
        "timeout":str(POLL_TIMEOUT),
        "offset":str(offset),
        "allowed_updates":json.dumps(["message","edited_message","channel_post"]),
    })
    req=urllib.request.Request(f"{BASE}/getUpdates?{qs}")
    with urllib.request.urlopen(req, timeout=POLL_TIMEOUT+20) as r:
        return json.loads(r.read().decode("utf-8","replace"))
def ensure_tables(con:sqlite3.Connection):
    con.execute("pragma journal_mode=WAL;")
    con.execute("pragma synchronous=NORMAL;")
    con.execute("pragma busy_timeout=8000;")
    con.execute("create table if not exists tg_ingest_state (id integer primary key, last_update_id integer)")
    con.execute("create table if not exists tg_private_ingest_state (id integer primary key, last_update_id integer)")
    con.execute("""
create table if not exists tg_private_chat_log (
  id integer primary key autoincrement,
  message_id integer,
  text text,
  created_at datetime default current_timestamp
)
""")
    con.execute("""
create table if not exists inbox_commands (
  id integer primary key autoincrement,
  chat_id text,
  message_id integer,
  reply_to_message_id integer,
  from_username text,
  from_name text,
  text text,
  received_at text,
  applied_at text,
  status text,
  error text,
  processed integer default 0
)
""")
    con.execute("insert or ignore into tg_ingest_state(id,last_update_id) values(1,0)")
    con.execute("insert or ignore into tg_private_ingest_state(id,last_update_id) values(1,0)")
    con.commit()
def get_offset(con:sqlite3.Connection)->int:
    r=con.execute("select last_update_id from tg_ingest_state where id=1").fetchone()
    last=int(r[0]) if r and r[0] is not None else 0
    return last+1 if last>0 else 0
def set_last(con:sqlite3.Connection, last_update_id:int):
    con.execute("update tg_ingest_state set last_update_id=? where id=1", (int(last_update_id),))
    con.execute("update tg_private_ingest_state set last_update_id=? where id=1", (int(last_update_id),))
    con.commit()
def ingest_update(con:sqlite3.Connection, upd:dict):
    m=upd.get("message") or {}
    if not m:
        return
    chat=m.get("chat") or {}
    chat_id=chat.get("id")
    if chat_id is None:
        return
    text=m.get("text") or ""
    msg_id=m.get("message_id")
    reply_to=(m.get("reply_to_message") or {}).get("message_id")
    frm=m.get("from") or {}
    from_u=frm.get("username")
    from_name=(" ".join([x for x in [frm.get("first_name"), frm.get("last_name")] if x]) or "").strip()
    if isinstance(chat_id,int) and chat_id > 0:
        con.execute(
            "insert into tg_private_chat_log(message_id,text,created_at) values(?,?,?)",
            (msg_id, text, now()),
        )
    else:
        con.execute(
            "insert into inbox_commands(chat_id,message_id,reply_to_message_id,from_username,from_name,text,received_at,status,processed) values(?,?,?,?,?,?,?,?,0)",
            (str(chat_id), msg_id, reply_to, from_u, from_name, text, now(), "queued"),
        )
def main():
    if not TOKEN:
        print("ERR missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        sys.exit(1)
    lock_f=open(LOCK_PATH,"w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("LOCKED_ALREADY_EXIT", LOCK_PATH, file=sys.stderr)
        sys.exit(0)
    print("TG_MUX_V2 DB_PATH=", DB_PATH)
    con=sqlite3.connect(DB_PATH, timeout=30)
    ensure_tables(con)
    backoff=0.5
    while True:
        try:
            offset=get_offset(con)
            data=call_getupdates(offset)
            res=data.get("result") or []
            if res:
                max_upd=max(int(u.get("update_id",0)) for u in res)
                for u in res:
                    ingest_update(con,u)
                con.commit()
                set_last(con,max_upd)
                backoff=0.5
            else:
                time.sleep(0.6)
        except urllib.error.HTTPError as e:
            if e.code==409:
                print("ERR 409_CONFLICT", file=sys.stderr)
                sys.exit(2)
            print("ERR HTTPError", repr(e), file=sys.stderr)
            time.sleep(min(10, backoff))
            backoff=min(10, backoff*2)
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(min(10, backoff))
                backoff=min(10, backoff*2)
                continue
            print("ERR", repr(e), file=sys.stderr)
            time.sleep(min(10, backoff))
            backoff=min(10, backoff*2)
        except Exception as e:
            print("ERR", repr(e), file=sys.stderr)
            time.sleep(min(10, backoff))
            backoff=min(10, backoff*2)
if __name__=="__main__":
    main()
