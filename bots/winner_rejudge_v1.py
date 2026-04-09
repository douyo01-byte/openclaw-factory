from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 30.0

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("""
    create table if not exists winner_rejudge_log (
      id integer primary key,
      winner_project_id integer,
      avg_score integer,
      decision text,
      note text,
      created_at text default (datetime('now'))
    )
    """)

    winner = cur.execute("""
    select id, theme
    from active_projects
    where status='winner'
    limit 1
    """).fetchone()

    if not winner:
        con.close()
        print("no_winner", flush=True)
        return

    rows = cur.execute("""
    select score
    from winner_learning_log
    order by exec_task_id desc
    limit 5
    """).fetchall()

    if not rows:
        con.close()
        print("no_learning", flush=True)
        return

    scores = [int(r["score"]) for r in rows]
    avg_score = sum(scores) // len(scores)

    decision = "keep"
    note = "stable"

    if avg_score < 30:
        decision = "pause_winner"
        note = "low_avg_score"

        cur.execute("""
        update active_projects
        set status='paused'
        where id=?
        """, (winner["id"],))

    elif avg_score >= 60:
        decision = "keep_winner"
        note = "high_avg_score"

    cur.execute("""
    insert into winner_rejudge_log
    (winner_project_id, avg_score, decision, note, created_at)
    values (?,?,?,?,datetime('now'))
    """, (winner["id"], avg_score, decision, note))

    con.commit()
    con.close()
    print(f"avg_score={avg_score} decision={decision}", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"[winner_rejudge_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)
