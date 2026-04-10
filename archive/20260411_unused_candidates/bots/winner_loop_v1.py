from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 20.0

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    row = cur.execute("""
    select id, theme
    from active_projects
    where status='winner'
    limit 1
    """).fetchone()

    if not row:
        con.close()
        print("no_winner", flush=True)
        return

    exists = cur.execute("""
    select 1
    from router_tasks
    where target_bot='kaikun04'
      and status in ('new','started')
      and coalesce(task_text,'') like '[WINNER_LOOP]%'
    limit 1
    """).fetchone()

    if exists:
        con.close()
        print("loop_skip_existing", flush=True)
        return

    theme = row["theme"]

    cur.execute("""
    insert into router_tasks
    (task_role,target_bot,mode,status,task_text,created_at,updated_at)
    values
    ('AI','kaikun04','THINK','new',?,datetime('now'),datetime('now'))
    """, (f"[WINNER_LOOP] この案件だけを前に進めろ。次の1手だけ決めろ。テーマ: {theme}",))

    con.commit()
    con.close()
    print("loop_push", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"[winner_loop_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)
