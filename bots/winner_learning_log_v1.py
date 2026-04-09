from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 10.0

def infer_score(task_text: str, result_text: str) -> int:
    score = 0
    t = (task_text or "") + "\n" + (result_text or "")
    if "runbook_gen_exec" in t:
        score += 40
    if "task=" in t:
        score += 30
    if "runbook_" in t:
        score += 20
    if "lp_" in t:
        score += 10
    return score

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("""
    create table if not exists winner_learning_log (
      exec_task_id integer primary key,
      parent_task_id integer,
      project_theme text,
      score integer,
      note text,
      created_at text default (datetime('now'))
    )
    """)

    rows = cur.execute("""
    select r.id as exec_task_id,
           coalesce(r.parent_task_id,0) as parent_task_id,
           coalesce(r.task_text,'') as task_text,
           coalesce(r.result_text,'') as result_text,
           coalesce(p.task_text,'') as parent_task_text
    from router_tasks r
    left join router_tasks p on p.id = r.parent_task_id
    where r.target_bot='ops_exec'
      and r.status='done'
      and r.id not in (select exec_task_id from winner_learning_log)
      and (
        coalesce(p.task_text,'') like '[WINNER_ONLY]%%'
        or coalesce(p.task_text,'') like '[WINNER_LOOP]%%'
      )
    order by r.id asc
    limit 20
    """).fetchall()

    done = 0
    for row in rows:
        score = infer_score(row["task_text"], row["task_text"])
        note = "generated_artifact" if "generated:" in row["result_text"] else "done"
        cur.execute("""
        insert into winner_learning_log(exec_task_id,parent_task_id,project_theme,score,note,created_at)
        values(?,?,?,?,?,datetime('now'))
        """, (
            row["exec_task_id"],
            row["parent_task_id"],
            row["parent_task_text"],
            score,
            note
        ))
        done += 1

    con.commit()
    con.close()
    print(f"[winner_learning_log_v1] done={done}", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"[winner_learning_log_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)
