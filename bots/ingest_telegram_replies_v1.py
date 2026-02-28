import os, json, sqlite3, urllib.request, urllib.parse, datetime

DB_PATH = os.environ.get("DB_PATH", "data/openclaw.db")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

def db():
    return sqlite3.connect(DB_PATH)

def cols(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}

def ensure(conn):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
    conn.execute("""CREATE TABLE IF NOT EXISTS inbox_commands(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 chat_id TEXT,
 message_id INTEGER,
 reply_to_message_id INTEGER,
 from_username TEXT,
 from_name TEXT,
 text TEXT NOT NULL,
 received_at TEXT NOT NULL DEFAULT (datetime("now")),
 applied_at TEXT,
 status TEXT DEFAULT "new",
 error TEXT
)""")")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_chat_msg ON inbox_commands(chat_id, message_id)")
    dc = {r[1] for r in conn.execute("PRAGMA table_info(decisions)")}
    if "run_id" not in dc: conn.execute("ALTER TABLE decisions ADD COLUMN run_id TEXT")
    if "target" not in dc: conn.execute("ALTER TABLE decisions ADD COLUMN target TEXT")
    if "meta_json" not in dc: conn.execute("ALTER TABLE decisions ADD COLUMN meta_json TEXT")


def kv_get(conn, k, default=None):
    row = conn.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return row[0] if row else default

def kv_set(conn, k, v):
    conn.execute("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))

def http_get(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + q, headers={"User-Agent":"openclaw"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_text(text):
    t=(text or "").strip()
    if not t: return None
    u=t.upper()
    if u.startswith("OK"):
        d="adopt"; rest=t[2:].strip()
    elif u.startswith("NO"):
        d="reject"; rest=t[2:].strip()
    elif u.startswith("NG"):
        d="reject"; rest=t[2:].strip()
    elif u.startswith("HOLD"):
        d="hold"; rest=t[4:].strip()
    elif t.startswith("採用"):
        d="adopt"; rest=t[len("採用"):].strip()
    elif t.startswith("見送り"):
        d="reject"; rest=t[len("見送り"):].strip()
    elif t.startswith("保留"):
        d="hold"; rest=t[len("保留"):].strip()
    else:
        return None
    target=""
    reason=""
    if rest:
        parts=rest.split(" ",1)
        target=parts[0].strip()
        reason=(parts[1].strip() if len(parts)>1 else "")
    return d,target,reason

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    with db() as conn:
        ensure(conn)
        offset = kv_get(conn, "tg_offset", None)
    params = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    if offset is not None:
        try:
            params["offset"] = int(offset)
        except:
            pass
    data = http_get(API, params)
    if not data.get("ok"):
        raise SystemExit(1)
    updates = data.get("result", [])
    if not updates:
        return
    max_update_id = None
    with db() as conn:
        ensure(conn)
        for upd in updates:
            uid = upd.get("update_id")
            if uid is None:
                continue
            max_update_id = uid if max_update_id is None else max(max_update_id, uid)
            msg = upd.get("message") or {}
            chat = msg.get("chat") or {}
            frm = msg.get("from") or {}
            text = msg.get("text") or ""
            conn.execute(
                "INSERT OR IGNORE INTO inbox_commands(chat_id, message_id, reply_to_message_id, from_username, from_name, text, received_at) VALUES(?,?,?,?,?,?,?)",
                (str(chat.get("id","")), int(msg.get("message_id") or 0), int((msg.get("reply_to_message") or {}).get("message_id") or 0), str((frm.get("username") or "")), str((frm.get("first_name") or "")), text, now())
            )
            parsed = parse_text(text)
            if parsed:
                decision, target, reason = parsed
                meta = {"chat_id": chat.get("id"), "message_id": msg.get("message_id"), "update_id": uid, "raw": text}
                conn.execute(
                    "INSERT INTO decisions(run_id, target, decision, reason, meta_json, created_at) VALUES(?,?,?,?,?,?)",
                    (os.environ.get("RUN_ID"), target, decision, reason, json.dumps(meta, ensure_ascii=False), now())
                )
        if max_update_id is not None:
            if max_update_id is not None: kv_set(conn, "tg_offset", int(max_update_id) + 1)

if __name__ == "__main__":
    main()
