from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 5.0

def choose_exec(task_text: str, reply_text: str) -> str:
    t = ((task_text or "") + "\n" + (reply_text or "")).strip()
    if "売上改善" in t:
        return "[EXEC]\nscript=run_python.sh\narg=mode=runbook_gen_exec;task=売上改善の最優先訴求1件について検証手順と確認項目を作成"
    if "競合差別化" in t or "差別化" in t:
        return "[EXEC]\nscript=run_python.sh\narg=mode=runbook_gen_exec;task=競合差別化の比較表と初回検証手順を作成"
    if "海外で売れる日本商品" in t:
        return "[EXEC]\nscript=run_python.sh\narg=mode=runbook_gen_exec;task=海外で売れる日本商品の候補1件を比較表にして検証手順を作成"
    return "[EXEC]\nscript=log_check.sh"

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("""
    create table if not exists winner_exec_bridge_log (
      task_id integer primary key,
      exec_task_id integer default 0,
      created_at text default (datetime('now'))
    )
    """)

    rows = cur.execute("""
    select id, task_text, coalesce(reply_text,'') as reply_text
    from router_tasks
    where target_bot='kaikun04'
      and status in ('new','done')
      and (
        coalesce(task_text,'') like '[WINNER_ONLY]%'
        or coalesce(task_text,'') like '[WINNER_LOOP]%'
      )
      and id not in (select task_id from winner_exec_bridge_log)
    order by id asc
    limit 20
    """).fetchall()

    done = 0
    for r in rows:
        exec_text = choose_exec(r["task_text"], r["reply_text"])
        cur.execute("""
        insert into router_tasks
        (source_command_id,parent_task_id,task_role,target_bot,mode,status,task_text,created_at,updated_at)
        values
        (0,?,'AI','ops_exec','EXEC','new',?,datetime('now'),datetime('now'))
        """, (r["id"], exec_text))
        exec_id = cur.execute("select last_insert_rowid()").fetchone()[0]

        cur.execute("""
        insert into winner_exec_bridge_log(task_id, exec_task_id, created_at)
        values(?,?,datetime('now'))
        """, (r["id"], exec_id))

        cur.execute("""
        update router_tasks
        set status='done',
            reply_text='[WINNER_EXEC_BRIDGED]\nexec_task_id=' || ?,
            updated_at=datetime('now')
        where id=?
        """, (exec_id, r["id"]))

        done += 1

    con.commit()
    con.close()
    print(f"[winner_exec_bridge_v1] done={done}", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"[winner_exec_bridge_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)
