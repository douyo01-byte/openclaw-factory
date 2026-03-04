import os, sys, json, time, re, urllib.parse, urllib.request, sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("env/telegram_daemon.env", override=True)

TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
API = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"

OFFSET_FILE = Path("data/tg_offset.txt")
OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)

def ensure_tables(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS proposal_conversation (
      id integer primary key autoincrement,
      proposal_id integer,
      role text,
      message text,
      created_at datetime default current_timestamp
    );
    """)
    conn.commit()

def load_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip())
    except Exception:
        return 0

def save_offset(v: int):
    OFFSET_FILE.write_text(str(v))

def extract_pid(text: str):
    m = re.search(r"#\s*(\d+)", text)
    return int(m.group(1)) if m else None

def save_conversation(conn: sqlite3.Connection, pid: int, text: str):
    conn.execute(
        "insert into proposal_conversation(proposal_id,role,message,created_at) values(?,?,?,datetime('now'))",
        (pid, "human", text),
    )
    conn.commit()

def fetch_updates(offset: int):
    qs = urllib.parse.urlencode({
        "offset": offset,
        "timeout": 0,
        "allowed_updates": json.dumps(["message"]),
    })
    req = urllib.request.Request(f"{API}?{qs}")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))

def tick_once():
    if not TOKEN:
        sys.stderr.write("ERR: TELEGRAM_BOT_TOKEN missing\n")
        return

    sys.stderr.write(f"INGEST_DB_PATH={DB_PATH}\n")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    ensure_tables(conn)

    offset = load_offset()
    data = fetch_updates(offset)
    if not data.get("ok"):
        sys.stderr.write("ERR: getUpdates not ok\n")
        conn.close()
        return

    results = data.get("result") or []
    if not results:
        conn.close()
        return

    max_u = offset
    for upd in results:
        uid = upd.get("update_id")
        if isinstance(uid, int) and uid >= max_u:
            max_u = uid + 1

        msg = upd.get("message") or {}
        text = (msg.get("text") or "").strip()
        if not text:
            continue

        pid = extract_pid(text)
        if pid is None:
            continue

        try:
            save_conversation(conn, pid, text)
            sys.stderr.write(f"saved pid={pid}\n")
        except Exception as e:
            sys.stderr.write(f"ERR: save_conversation pid={pid} {repr(e)}\n")

    save_offset(max_u)
    conn.close()

def main():
    while True:
        try:
            tick_once()
        except Exception as e:
            sys.stderr.write(f"ERR: tick_once {repr(e)}\n")
        time.sleep(2)

if __name__ == "__main__":
    main()
