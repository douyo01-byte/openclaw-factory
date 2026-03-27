#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request

DB = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
BOT_TOKEN = (os.environ.get("KAIKUN04_ROUTER_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
CHAT_ID_RE = re.compile(r"^-?\d+$")

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma journal_mode=WAL")
    c.execute("pragma busy_timeout=30000")
    return c

def safe_text(t: str) -> str:
    t = (t or "").strip()
    if len(t) > 4000:
        t = t[:4000] + "\n...(truncated)"
    return t

def valid_chat_id(chat_id: str) -> bool:
    return bool(chat_id and CHAT_ID_RE.match(str(chat_id).strip()))

def tg_send(chat_id: str, text: str) -> str:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN empty")
    if not valid_chat_id(chat_id):
        raise RuntimeError(f"invalid_chat_id:{chat_id}")
    payload = {
        "chat_id": chat_id,
        "text": safe_text(text),
        "disable_web_page_preview": True,
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(API, data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    j = json.loads(body)
    if not j.get("ok"):
        raise RuntimeError(body[:1000])
    return str(j["result"]["message_id"])

def fetch_rows(c):
    return c.execute("""
        select id, job_id, chat_id, message_text
        from conversation_outbox
        where coalesce(status,'')='new'
        order by id asc
        limit 10
    """).fetchall()

def run_once():
    c = conn()
    rows = fetch_rows(c)
    done = 0
    for r in rows:
        try:
            mid = tg_send(r["chat_id"], r["message_text"])
            c.execute("""
                update conversation_outbox
                set status='sent',
                    sent_message_id=?,
                    error='',
                    updated_at=datetime('now')
                where id=?
            """, (mid, r["id"]))
            c.execute("""
                update conversation_jobs
                set final_reply_status='sent',
                    updated_at=datetime('now')
                where id=?
            """, (r["job_id"],))
            print(f"sent outbox_id={r['id']} job_id={r['job_id']} message_id={mid}", flush=True)
            done += 1
        except Exception as e:
            msg = str(e)[:1000]
            status = "skipped" if msg.startswith("invalid_chat_id:") else "error"
            job_status = "skipped_invalid_chat_id" if status == "skipped" else "send_error"
            c.execute("""
                update conversation_outbox
                set status=?,
                    error=?,
                    updated_at=datetime('now')
                where id=?
            """, (status, msg, r["id"]))
            c.execute("""
                update conversation_jobs
                set final_reply_status=?,
                    updated_at=datetime('now')
                where id=?
            """, (job_status, r["job_id"]))
            print(f"{status} outbox_id={r['id']} job_id={r['job_id']} err={msg}", flush=True)
    c.commit()
    c.close()
    print(f"send_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
