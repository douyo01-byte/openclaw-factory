import os, json, sqlite3, requests, datetime

DAEMON_DB = os.environ.get("DB_PATH", "data/openclaw.db")
FACTORY_DB = os.environ.get("FACTORY_DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def one(conn, q, a=()):
    r = conn.execute(q, a).fetchone()
    return r[0] if r else None

def ensure(d):
    d.execute("""CREATE TABLE IF NOT EXISTS tg_prompt_map(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      chat_id TEXT NOT NULL,
      message_id INTEGER NOT NULL,
      proposal_id INTEGER NOT NULL,
      kind TEXT NOT NULL DEFAULT 'spec_question',
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    d.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tg_prompt_map_chat_msg ON tg_prompt_map(chat_id,message_id)")
    d.execute("CREATE INDEX IF NOT EXISTS idx_tg_prompt_map_proposal ON tg_prompt_map(proposal_id)")
    d.execute("""CREATE TABLE IF NOT EXISTS sent_questions(
      proposal_id INTEGER PRIMARY KEY,
      chat_id TEXT NOT NULL,
      message_id INTEGER NOT NULL,
      sent_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

def main():
    if not TOKEN:
        raise SystemExit("missing TELEGRAM_BOT_TOKEN")
    d = sqlite3.connect(DAEMON_DB)
    d.execute("PRAGMA journal_mode=WAL;")
    d.execute("PRAGMA busy_timeout=5000;")
    ensure(d)

    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        chat_id = one(d, "SELECT chat_id FROM inbox_commands WHERE chat_id IS NOT NULL AND chat_id!='' ORDER BY id DESC LIMIT 1")
    if not chat_id:
        raise SystemExit("missing TELEGRAM_CHAT_ID (and no inbox_commands chat_id)")

    f = sqlite3.connect(FACTORY_DB)
    f.row_factory = sqlite3.Row

    rows = f.execute("""
      SELECT proposal_id, stage, COALESCE(pending_question,'') AS q
      FROM proposal_state
      WHERE stage='waiting_answer' AND COALESCE(pending_question,'')!=''
      ORDER BY updated_at ASC
      LIMIT 20
    """).fetchall()

    sent = 0
    for r in rows:
        pid = int(r["proposal_id"])
        if one(d, "SELECT 1 FROM sent_questions WHERE proposal_id=?", (pid,)):
            continue

        text = f"【仕様確認 #{pid}】\n{r['q']}\n\n返信で OK / NG / HOLD だけ送ってください。"
        resp = requests.post(API, data={"chat_id": str(chat_id), "text": text}, timeout=20)
        resp.raise_for_status()
        j = resp.json()
        mid = int((j.get("result") or {}).get("message_id") or 0)
        if not mid:
            raise SystemExit("sendMessage no message_id: " + json.dumps(j, ensure_ascii=False))

        d.execute("INSERT OR IGNORE INTO tg_prompt_map(chat_id,message_id,proposal_id,kind,created_at) VALUES(?,?,?,?,?)",
                  (str(chat_id), mid, pid, "spec_question", now()))
        d.execute("INSERT OR REPLACE INTO sent_questions(proposal_id,chat_id,message_id,sent_at) VALUES(?,?,?,?)",
                  (pid, str(chat_id), mid, now()))
        d.commit()
        sent += 1

    print(f"Done. sent={sent}")

if __name__ == "__main__":
    main()
