import os, json, sqlite3, urllib.request, urllib.parse

DB_PATH = os.environ.get("DB_PATH", "data/openclaw.db")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

def db():
    return sqlite3.connect(DB_PATH)

def kv_get(conn, k, default=None):
    cur = conn.execute("SELECT v FROM kv WHERE k=?", (k,))
    row = cur.fetchone()
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
    decision = None
    if u.startswith("OK " ) or u == "OK":
        decision = "adopt"
        rest = t[2:].strip()
    elif u.startswith("NO ") or u == "NO":
        decision = "reject"
        rest = t[2:].strip()
    elif u.startswith("HOLD ") or u == "HOLD":
        decision = "hold"
        rest = t[4:].strip()
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
            reason = ""
    return decision, target, reason

def main():
    with db() as conn:
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
        for upd in updates:
            uid = upd.get("update_id")
            if uid is None:
                continue
            max_update_id = uid if max_update_id is None else max(max_update_id, uid)
            msg = upd.get("message") or {}
            chat = msg.get("chat") or {}
            frm = msg.get("from") or {}
            text = msg.get("text") or ""
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO inbox_commands(source, update_id, chat_id, user_id, text) VALUES(?,?,?,?,?)",
                    ("telegram", str(uid), str(chat.get("id","")), str(frm.get("id","")), text)
                )
            except:
                pass
            parsed = parse_text(text)
            if parsed:
                decision, target, reason = parsed
                meta = {"chat_id": chat.get("id"), "user_id": frm.get("id"), "raw": text, "update_id": uid}
                conn.execute(
                    "INSERT INTO decisions(run_id, target, decision, reason, meta_json) VALUES(?,?,?,?,?)",
                    (os.environ.get("RUN_ID"), target, decision, reason, json.dumps(meta, ensure_ascii=False))
                )
        if max_update_id is not None:
            kv_set(conn, "tg_offset", int(max_update_id) + 1)

if __name__ == "__main__":
    main()
