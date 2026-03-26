import os
import time
import sqlite3
import urllib.parse
import urllib.request
import json

DB = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH")
BOT_TOKEN = (os.environ.get("KAIKUN04_ROUTER_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_ID = (os.environ.get("KAIKUN04_ROUTER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma journal_mode=WAL")
    c.execute("pragma busy_timeout=30000")
    return c

def safe_text(t: str) -> str:
    if not t:
        return t
    t = t.strip()
    # Telegram制限対策（4000で切る）
    if len(t) > 4000:
        t = t[:4000] + "\n...(truncated)"
    return t

def tg_send(text):
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(API, data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read().decode("utf-8", errors="ignore")
    j = json.loads(body)
    return str(((j.get("result") or {}).get("message_id") or ""))

def tick():
    c = conn()
    try:
        rows = c.execute("""
            select rt.id as task_id, rt.reply_text, ic.id as cmd_id
            from router_tasks rt
            join inbox_commands ic on ic.id = rt.source_command_id
            where coalesce(rt.status,'')='done'
              and coalesce(rt.reply_text,'')<>''
              and coalesce(ic.router_finish_status,'')='applied'
            order by rt.id asc
            limit 20
        """).fetchall()
        done = 0
        touched = len(rows)
        for r in rows:
            try:
                mid = tg_send(safe_text(r["reply_text"]))
                c.execute("""
                    update router_tasks
                    set sent_message_id=?,
                        updated_at=datetime('now')
                    where id=?
                """, (mid, r["task_id"]))
                c.execute("""
                    update inbox_commands
                    set status='done',
                        processed=1,
                        router_finish_status='sent',
                        router_task_id=?,
                        updated_at=datetime('now')
                    where id=?
                """, (r["task_id"], r["cmd_id"]))
                c.commit()
                done += 1
                print(f"[router_reply_finisher_v1] sent task_id={r['task_id']} user_mid={mid}", flush=True)
            except Exception as e:
                print(f"[router_reply_finisher_v1] error task_id={r['task_id']} err={e!r}", flush=True)
        print(f"[router_reply_finisher_v1] done={done} touched={touched}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[router_reply_finisher_v1] fatal err={e!r}", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    main()
