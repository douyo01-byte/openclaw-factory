from __future__ import annotations
import os
import time
import sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("ROUTER_TIMEOUT_FALLBACK_SLEEP", "8"))

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
    if "fallback_sent_at" not in cols:
        c.execute("alter table router_tasks add column fallback_sent_at text default ''")
    if "fallback_text" not in cols:
        c.execute("alter table router_tasks add column fallback_text text default ''")

def build_fallback(task):
    return "\n".join([
        f"[TASK_ID:{task['id']}]",
        "THINK応答が時間内に完了しなかったため、簡易回答へ切り替えました。",
        "要点を短く返します。",
        "必要ならもう一度 [THINK] を付けて再依頼してください。"
    ])

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
        select
          id,
          source_command_id,
          coalesce(reply_text,'') as reply_text,
          coalesce(result_text,'') as result_text,
          coalesce(fallback_sent_at,'') as fallback_sent_at
        from router_tasks
        where coalesce(status,'')='timeout'
          and coalesce(target_bot,'')='kaikun04'
          and coalesce(reply_text,'')=''
          and coalesce(fallback_sent_at,'')=''
        order by id asc
        limit 20
        """).fetchall()
        done = 0
        for r in rows:
            fb = build_fallback(r)
            c.execute("""
            insert into inbox_commands(
              source, text, status, created_at, updated_at,
              processed, router_status, router_target, router_mode, router_finish_status
            ) values(
              'router_timeout_fallback', ?, 'done', datetime('now'), datetime('now'),
              1, 'fallback_sent', 'kaikun02', 'FAST', 'fallback'
            )
            """, (fb,))
            c.execute("""
            update router_tasks
            set fallback_sent_at=datetime('now'),
                fallback_text=?,
                updated_at=datetime('now'),
                result_text=case
                  when coalesce(result_text,'')=''
                    then 'fallback_sent'
                  when instr(coalesce(result_text,''), 'fallback_sent')>0
                    then result_text
                  else result_text || ' | fallback_sent'
                end
            where id=?
            """, (fb, int(r["id"])))
            done += 1
        if done:
            c.commit()
        print(f"[router_timeout_fallback_v1] done={done}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[router_timeout_fallback_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
