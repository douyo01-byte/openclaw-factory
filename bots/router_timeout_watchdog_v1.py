from __future__ import annotations
import os, time, sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("ROUTER_TIMEOUT_WATCHDOG_SLEEP", "8"))

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
    if "timeout_sec" not in cols:
        c.execute("alter table router_tasks add column timeout_sec integer not null default 300")

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
        select id, timeout_sec
        from router_tasks
        where coalesce(status,'')='started'
          and coalesce(started_at,'')<>''
          and (strftime('%s','now') - strftime('%s', started_at)) >= coalesce(timeout_sec,300)
        order by id asc
        limit 20
        """).fetchall()

        done = 0
        for r in rows:
            c.execute("""
            update router_tasks
            set status='timeout',
                finished_at=datetime('now'),
                updated_at=datetime('now'),
                result_text=coalesce(result_text,'') || case when coalesce(result_text,'')='' then '' else ' | ' end || 'timeout'
            where id=?
            """, (r["id"],))
            done += 1

        if done:
            c.commit()
        print(f"[router_timeout_watchdog_v1] timeout={done}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[router_timeout_watchdog_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
