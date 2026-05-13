#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)

def con():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def main():
    db = con()

    row = db.execute("""
        select id, task_text
        from router_tasks
        where status='new'
          and task_text like '%[REVENUE_CORE]%'
        order by id asc
        limit 1
    """).fetchone()

    if not row:
        print("no revenue core")
        return

    exec_text = """[EXEC]
script=run_python.sh
arg=mode=lpgen_exec;task=売上改善LP・Telegram導線・SNS訴求・CTA改善案を生成して成果物化
"""

    cur = db.execute("""
        insert into router_tasks
        (
          parent_task_id,
          target_bot,
          mode,
          status,
          task_text,
          created_at,
          updated_at
        )
        values
        (
          ?,
          'ops_exec',
          'EXEC',
          'new',
          ?,
          datetime('now'),
          datetime('now')
        )
    """, (row["id"], exec_text))

    db.execute("""
        update router_tasks
        set status='done',
            reply_text='REVENUE_EXEC_ROUTED',
            updated_at=datetime('now')
        where id=?
    """, (row["id"],))

    db.commit()

    print(
        f"routed revenue task parent={row['id']} child={cur.lastrowid}",
        flush=True
    )

if __name__ == "__main__":
    main()
