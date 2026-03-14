from __future__ import annotations
import os, time, sqlite3

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("ROUTER_REPLY_FINISHER_SLEEP", "8"))

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
    if "reply_text" not in cols:
        c.execute("alter table router_tasks add column reply_text text default ''")
    cols2 = {r["name"] for r in c.execute("pragma table_info(inbox_commands)").fetchall()}
    if "router_finish_status" not in cols2:
        c.execute("alter table inbox_commands add column router_finish_status text default ''")

def tick():
    c = conn()
    try:
        ensure_schema(c)

        replies = c.execute("""
        select id, coalesce(text,'') as text, coalesce(created_at,'') as created_at
        from inbox_commands
        where coalesce(router_finish_status,'')=''
          and coalesce(text,'')<>''
        order by id asc
        limit 20
        """).fetchall()

        done = 0
        touched = 0
        for r in replies:
            task = c.execute("""
            select id, target_bot
            from router_tasks
            where coalesce(status,'')='started'
            order by id asc
            limit 1
            """).fetchone()

            if not task:
                pending = c.execute("""
                select id
                from router_tasks
                where source_command_id=?
                  and coalesce(status,'') in ('new','started')
                order by id desc
                limit 1
                """, (r["id"],)).fetchone()
                if pending:
                    continue
                c.execute("""
                update inbox_commands
                set router_finish_status='no_started_task',
                    updated_at=datetime('now')
                where id=?
                """, (r["id"],))
                touched += 1
                continue

            c.execute("""
            update router_tasks
            set status='done',
                finished_at=datetime('now'),
                updated_at=datetime('now'),
                reply_text=?,
                result_text=coalesce(result_text,'') || ' | reply_received'
            where id=?
            """, (r["text"], task["id"]))

            c.execute("""
            update inbox_commands
            set router_finish_status='applied',
                updated_at=datetime('now')
            where id=?
            """, (r["id"],))

            done += 1
            touched += 1

        if touched:
            c.commit()
        print(f"[router_reply_finisher_v1] done={done} touched={touched} replies={len(replies)}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[router_reply_finisher_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
