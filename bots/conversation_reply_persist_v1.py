#!/usr/bin/env python3
import os
import sqlite3
import subprocess

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def fetch_jobs(c, limit=10):
    return c.execute(
        """
        select id
        from conversation_jobs
        where coalesce(current_phase,'') in ('lp_improved_done','image_plan_done','product_image_urls_done')
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'')=''
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def build_reply(job_id: int) -> str:
    out = subprocess.check_output(
        ["python3", "bots/conversation_artifact_reply_v1.py", str(job_id)],
        text=True
    )
    return out.strip()

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for row in rows:
        try:
            reply = build_reply(row["id"])
            c.execute(
                """
                update conversation_jobs
                set final_reply_text=?,
                    final_reply_status='ready',
                    updated_at=datetime('now')
                where id=?
                """,
                (reply, row["id"])
            )
            print(f"reply_ready job_id={row['id']}", flush=True)
            done += 1
        except Exception as e:
            c.execute(
                """
                update conversation_jobs
                set final_reply_status='error',
                    updated_at=datetime('now')
                where id=?
                """,
                (row["id"],)
            )
            print(f"reply_error job_id={row['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"reply_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
