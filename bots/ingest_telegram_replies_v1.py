import requests
import os
import json
import datetime
import time
import sqlite3
from dotenv import load_dotenv

load_dotenv("env/telegram_replies.env", override=False)

DB_PATH = os.environ.get("DB_PATH", "data/openclaw.db")
TOKEN = (
    os.environ.get("TELEGRAM_REPORT_BOT_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN", "")
).strip()
API = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_text(text):
    t = (text or "").strip()
    u = t.upper()
    if not t:
        return None
    if u.startswith("OK"):
        d, rest = "adopt", t[2:].strip()
    elif u.startswith("NO") or u.startswith("NG"):
        d, rest = "reject", t[2:].strip()
    elif u.startswith("HOLD"):
        d, rest = "hold", t[4:].strip()
    elif t.startswith("採 用 "):
        d, rest = "adopt", t[2:].strip()
    elif t.startswith("見 送 り "):
        d, rest = "reject", t[3:].strip()
    elif t.startswith("保 留 "):
        d, rest = "hold", t[2:].strip()
    else:
        return None
    target = ""
    reason = ""
    if rest:
        p = rest.split(" ", 1)
        target = p[0].strip()
        reason = p[1].strip() if len(p) > 1 else ""
    return d, target, reason

def kv_get(c, k):
    r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return r[0] if r else None

def kv_set(c, k, v):
    c.execute(
        "INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (k, str(v)),
    )

def ensure(c):
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=NORMAL;")
    c.execute("PRAGMA busy_timeout=30000;")
    c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
    c.execute("""CREATE TABLE IF NOT EXISTS proposal_state(
  proposal_id INTEGER PRIMARY KEY,
  stage TEXT,
  pending_questions TEXT,
  updated_at TEXT DEFAULT (datetime('now')),
  pending_question TEXT
)""")
    c.execute("""CREATE TABLE IF NOT EXISTS proposal_conversation(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER,
  role TEXT,
  message TEXT,
  created_at TEXT DEFAULT (datetime('now'))
)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tg_prompt_map(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  message_id INTEGER NOT NULL,
  proposal_id INTEGER NOT NULL,
  kind TEXT NOT NULL DEFAULT 'spec_question',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
)""")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tg_prompt_map_chat_msg ON tg_prompt_map(chat_id,message_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tg_prompt_map_proposal ON tg_prompt_map(proposal_id)")
    c.execute("""CREATE TABLE IF NOT EXISTS inbox_commands(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT,
  message_id INTEGER,
  reply_to_message_id INTEGER,
  from_username TEXT,
  from_name TEXT,
  text TEXT NOT NULL,
  received_at TEXT NOT NULL DEFAULT (datetime('now')),
  applied_at TEXT,
  status TEXT DEFAULT 'new',
  error TEXT,
  update_id INTEGER
)""")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_chat_msg ON inbox_commands(chat_id,message_id)")
    c.execute("""CREATE TABLE IF NOT EXISTS decisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  target TEXT,
  decision TEXT,
  reason TEXT,
  meta_json TEXT,
  created_at TEXT DEFAULT (datetime('now'))
)""")
    dc = {r[1] for r in c.execute("PRAGMA table_info(decisions)")}
    if "run_id" not in dc:
        c.execute("ALTER TABLE decisions ADD COLUMN run_id TEXT")
    if "target" not in dc:
        c.execute("ALTER TABLE decisions ADD COLUMN target TEXT")
    if "meta_json" not in dc:
        c.execute("ALTER TABLE decisions ADD COLUMN meta_json TEXT")

def map_reply_to_proposal(c, chat_id, reply_to_message_id):
    if not chat_id or not reply_to_message_id:
        return None
    r = c.execute(
        "SELECT proposal_id FROM tg_prompt_map WHERE chat_id=? AND message_id=? ORDER BY id DESC LIMIT 1",
        (str(chat_id), int(reply_to_message_id)),
    ).fetchone()
    return int(r[0]) if r else None

def http_get(url, params):
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def exec_retry(conn, sql, params=(), tries=8, sleep_sec=0.5):
    last = None
    for _ in range(tries):
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as e:
            last = e
            if "locked" not in str(e).lower():
                raise
            time.sleep(sleep_sec)
    raise last
def parse_spec_reply(text):
    t = (text or "").strip()
    if not t.startswith("ID:"):
        return None, None
    parts = t.split(None, 1)
    try:
        pid = int(parts[0].replace("ID:", "").strip())
    except:
        return None, None
    body = parts[1].strip() if len(parts) > 1 else ""
    return pid, body

def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN empty")

    c = sqlite3.connect(DB_PATH)
    ensure(c)

    offset_key = "tg_offset_ceo" if (os.environ.get("TELEGRAM_CEO_BOT_TOKEN") or "").strip() and TOKEN == (os.environ.get("TELEGRAM_CEO_BOT_TOKEN") or "").strip() else "tg_offset"
    offset = kv_get(c, offset_key)
    params = {"timeout": 0}
    if offset is not None:
        params["offset"] = int(offset) + 1

    data = http_get(API, params)
    updates = data.get("result") or []

    seen = 0
    for upd in updates:
        uid = upd.get("update_id")
        msg = upd.get("message") or {}
        if uid is None:
            continue

        chat = msg.get("chat") or {}
        frm = msg.get("from") or {}
        text = msg.get("text") or ""
        chat_id = str(chat.get("id", ""))
        message_id = int(msg.get("message_id") or 0)
        reply_id = int(((msg.get("reply_to_message") or {}).get("message_id")) or 0)
        from_username = str(frm.get("username") or "")
        from_name = str(frm.get("first_name") or "")

        exec_retry(c,
            """INSERT OR IGNORE INTO inbox_commands(
                chat_id, message_id, reply_to_message_id, from_username, from_name, text, received_at, update_id
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (chat_id, message_id, reply_id, from_username, from_name, text, now(), uid),
        )

        spec_pid, spec_body = parse_spec_reply(text)
        if spec_pid:
            exec_retry(c,
                "INSERT INTO proposal_conversation(proposal_id,role,message,created_at) VALUES(?,?,?,?)",
                (spec_pid, "human", spec_body, now()),
            )
            exec_retry(c,
                """INSERT INTO proposal_state(proposal_id,stage,updated_at)
                VALUES(?, 'answer_received', ?)
                ON CONFLICT(proposal_id) DO UPDATE SET
                  stage='answer_received',
                  updated_at=excluded.updated_at""",
                (spec_pid, now()),
            )
            exec_retry(c,
                "UPDATE dev_proposals SET spec_stage='answer_received' WHERE id=?",
                (spec_pid,),
            )

        p = parse_text(text)
        if p:
            decision, target, reason = p
            if (not target) and reply_id:
                pid = map_reply_to_proposal(c, chat_id, reply_id)
                if pid is not None:
                    target = str(pid)
            meta = {
                "chat_id": chat.get("id"),
                "message_id": msg.get("message_id"),
                "update_id": uid,
                "raw": text,
            }
            exec_retry(c,
                "INSERT INTO decisions(run_id,target,decision,reason,meta_json,created_at) VALUES(?,?,?,?,?,?)",
                (
                    os.environ.get("RUN_ID"),
                    target,
                    decision,
                    reason,
                    json.dumps(meta, ensure_ascii=False),
                    now(),
                ),
            )

        kv_set(c, offset_key, int(uid) + 1)
        c.commit()
        seen += 1

    c.close()
    print(f"ingest_seen={seen}", flush=True)

if __name__ == "__main__":
    main()
