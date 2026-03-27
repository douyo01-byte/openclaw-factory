#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def fetch_jobs(c, limit=20):
    return c.execute(
        """
        select id, source_chat_id, final_reply_text
        from conversation_jobs
        where coalesce(final_reply_status,'')='ready'
          and coalesce(final_reply_text,'')<>''
          and id not in (
            select job_id from conversation_outbox
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 20)
    done = 0
    for row in rows:
        try:
            c.execute(
                """
                insert into conversation_outbox(
                  job_id, chat_id, message_text, status, created_at, updated_at
                ) values(?,?,?,'new',datetime('now'),datetime('now'))
                """,
                (row["id"], row["source_chat_id"] or "", row["final_reply_text"])
            )
            c.execute(
                """
                update conversation_jobs
                set final_reply_status='queued',
                    updated_at=datetime('now')
                where id=?
                """,
                (row["id"],)
            )
            print(f"queued job_id={row['id']}", flush=True)
            done += 1
        except Exception as e:
            c.execute(
                """
                update conversation_jobs
                set final_reply_status='queue_error',
                    updated_at=datetime('now')
                where id=?
                """,
                (row["id"],)
            )
            print(f"queue_error job_id={row['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"queue_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
