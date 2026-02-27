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
    conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
    conn.execute("""CREATE TABLE IF NOT EXISTS inbox_commands(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      update_id TEXT NOT NULL,
      chat_id TEXT,
      user_id TEXT,
      text TEXT NOT NULL,
      received_at TEXT,
      UNIQUE(source, update_id)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inbox_commands_received_at ON inbox_commands(received_at)")
    conn.execute("""CREATE TABLE IF NOT EXISTS decisions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id TEXT,
      target TEXT,
      decision TEXT,
      reason TEXT,
      meta_json TEXT,
      created_at TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at)")
    ic = cols(conn, "inbox_commands")
    if "received_at" not in ic:
        conn.execute("ALTER TABLE inbox_commands ADD COLUMN received_at TEXT")
    dc = cols(conn, "decisions")
    for c in ["run_id","target","decision","reason","meta_json","created_at"]:
        if c not in dc:
            conn.execute(f"ALTER TABLE decisions ADD COLUMN {c} TEXT")

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
    t = (text or "").strip()
    if not t:
        return None
    u = t.upper()
    if u.startswith("OK") or t.startswith("採用") or t.startswith("A"):
        decision = "adopt"
        rest = t[2:].strip() if u.startswith("OK") else (t[2:].strip() if t.startswith("A") else t[2:].strip())
    elif u.startswith("NO") or t.startswith("見送り") or t.startswith("NG"):
        decision = "reject"
        rest = t[2:].strip() if u.startswith("NO") else t[3:].strip()
    elif u.startswith("HOLD") or t.startswith("保留"):
        decision = "hold"
        rest = t[4:].strip() if u.startswith("HOLD") else t[2:].strip()
    else:
        return None
    target = ""
    reason = ""
    if rest:
        if " " in rest:
            target, reason = rest.split(" ", 1)
            target = target.strip()
            reason = reason.strip()
        else:
            target = rest.strip()
    return decision, target, reason

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
                "INSERT OR IGNORE INTO inbox_commands(source, update_id, chat_id, user_id, text, received_at) VALUES(?,?,?,?,?,?)",
                ("telegram", str(uid), str(chat.get("id","")), str(frm.get("id","")), text, now())
            )
            parsed = parse_text(text)
            if parsed:
                decision, target, reason = parsed
                meta = {"chat_id": chat.get("id"), "user_id": frm.get("id"), "raw": text, "update_id": uid}
                conn.execute(
                    "INSERT INTO decisions(run_id, target, decision, reason, meta_json, created_at) VALUES(?,?,?,?,?,?)",
                    (os.environ.get("RUN_ID"), target, decision, reason, json.dumps(meta, ensure_ascii=False), now())
                )
        if max_update_id is not None:
            kv_set(conn, "tg_offset", int(max_update_id) + 1)

if __name__ == "__main__":
    main()
