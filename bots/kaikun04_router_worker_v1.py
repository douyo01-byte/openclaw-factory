from __future__ import annotations
import os, time, sqlite3, requests

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("KAIKUN04_ROUTER_WORKER_SLEEP", "8"))
BOT_TOKEN = (os.environ.get("KAIKUN04_ROUTER_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_ID = (os.environ.get("KAIKUN04_ROUTER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)").fetchall()}
    if "started_at" not in cols:
        c.execute("alter table router_tasks add column started_at text default ''")
    if "finished_at" not in cols:
        c.execute("alter table router_tasks add column finished_at text default ''")
    if "result_text" not in cols:
        c.execute("alter table router_tasks add column result_text text default ''")
    if "sent_message_id" not in cols:
        c.execute("alter table router_tasks add column sent_message_id text default ''")

def tg_send(text: str):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("kaikun04 telegram env missing")
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )
    r.raise_for_status()
    j = r.json()
    return str(((j.get("result") or {}).get("message_id") or ""))

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
        select id, task_text
        from router_tasks
        where coalesce(status,'new')='new'
          and coalesce(target_bot,'')='kaikun04'
        order by id asc
        limit 5
        """).fetchall()
        done = 0
        for r in rows:
            routed_text = f"[TASK_ID:{r['id']}]\n{r['task_text']}\n\n返信の先頭に [TASK_ID:{r['id']}] を付けてください。"
            sent_message_id = tg_send(routed_text)
            result = f"sent_to_kaikun04: {routed_text[:120]}"
            c.execute("""
            update router_tasks
            set status='started',
                started_at=datetime('now'),
                updated_at=datetime('now'),
                result_text=?,
                sent_message_id=?
            where id=?
            """, (result, sent_message_id, r["id"]))
            done += 1
        if done:
            c.commit()
        print(f"[kaikun04_router_worker_v1] done={done}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[kaikun04_router_worker_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
