import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure():
    with conn() as c:
        c.execute("CREATE INDEX IF NOT EXISTS idx_tg_private_chat_log_ingested ON tg_private_chat_log(router_ingested, id)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_commands_chat_msg ON inbox_commands(chat_id, message_id)")
        c.commit()

def run_once():
    done = 0
    with conn() as c:
        rows = c.execute("""
            select id, coalesce(update_id,0) as update_id, coalesce(message_id,0) as message_id,
                   coalesce(chat_id,0) as chat_id, coalesce(text,'') as text, coalesce(created_at,'') as created_at
            from tg_private_chat_log
            where coalesce(router_ingested,'')=''
            order by id asc
            limit 50
        """).fetchall()

        for r in rows:
            text = (r["text"] or "").strip()
            if not text:
                c.execute("""
                    update tg_private_chat_log
                    set router_ingested='skipped', router_ingested_at=datetime('now')
                    where id=?
                """, (int(r["id"]),))
                done += 1
                continue

            c.execute("""
                insert or ignore into inbox_commands(
                    source, text, status, created_at, updated_at,
                    chat_id, message_id, received_at, update_id, processed,
                    router_status, router_target, router_mode, router_finish_status
                ) values(
                    ?, ?, 'pending', datetime('now'), datetime('now'),
                    ?, ?, ?, ?, 0,
                    '', 'secretary', 'private_reply', ''
                )
            """, (
                "tg_private_chat_log",
                text,
                str(r["chat_id"]),
                int(r["message_id"]),
                r["created_at"] or "",
                int(r["update_id"]),
            ))

            c.execute("""
                update tg_private_chat_log
                set router_ingested='yes', router_ingested_at=datetime('now')
                where id=?
            """, (int(r["id"]),))
            done += 1

        c.commit()

    print(f"[private_reply_to_inbox_v1] done={done}", flush=True)

if __name__ == "__main__":
    while True:
        try:
            ensure()
            run_once()
        except Exception as e:
            print(f"[private_reply_to_inbox_v1][error] {repr(e)}", flush=True)
        time.sleep(5)
