import os, time, json, re, sqlite3, urllib.parse, urllib.request, unicodedata
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
API = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

def _realpath(p: str) -> str:
    return str(Path(p).resolve())

def db():
    rp = _realpath(DB_PATH)
    Path(rp).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(rp, timeout=30, isolation_level=None)
    con.execute("PRAGMA busy_timeout=8000")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con

def ensure_tables(con):
    con.execute("create table if not exists tg_ingest_state(id integer primary key, last_update_id integer not null)")
    con.execute("insert or ignore into tg_ingest_state(id,last_update_id) values(1,0)")
    con.execute("create table if not exists inbox_commands(id integer primary key autoincrement, status text, text text, created_at text default (datetime('now')))")
    con.execute("create index if not exists idx_inbox_commands_status on inbox_commands(status)")
    con.execute("create index if not exists idx_inbox_commands_created_at on inbox_commands(created_at)")

def get_offset(con):
    row = con.execute("select last_update_id from tg_ingest_state where id=1").fetchone()
    return int(row[0] or 0) if row else 0

def set_offset(con, uid):
    con.execute("update tg_ingest_state set last_update_id=? where id=1", (int(uid),))

def _oclaw_cmd_status(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = re.sub(r"\s+", "", t)
    if t in ("ping", "/ping"):
        return "applied"
    if re.match(r"^(承認|保留|質問|回答|任せます)#\d+", t):
        return "pending"
    return "ignored"

def fetch(offset: int):
    qs = urllib.parse.urlencode({"offset": offset + 1, "timeout": 0})
    req = urllib.request.Request(f"{API}?{qs}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    con = db()
    ensure_tables(con)
    while True:
        try:
            offset = get_offset(con)
            data = fetch(offset)
            for u in data.get("result", []):
                uid = int(u.get("update_id", 0))
                if uid:
                    set_offset(con, uid)
                msg = u.get("message") or u.get("edited_message") or {}
                txt = (msg.get("text") or "").strip()
                if not txt:
                    continue
                st = _oclaw_cmd_status(txt)
                con.execute("insert into inbox_commands(status,text) values(?,?)", (st, txt))
        except Exception:
            pass
        time.sleep(1)

if __name__ == "__main__":
    main()
