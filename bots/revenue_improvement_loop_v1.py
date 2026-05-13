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

    exp = db.execute("""
        select *
        from revenue_experiments
        where status='winner_candidate'
        order by id asc
        limit 1
    """).fetchone()

    if not exp:
        print("no winner candidate")
        return

    task_text = f"""[REVENUE_CORE_IMPROVE]
目的: 勝者候補をさらに改善して収益期待値を上げる。
対象experiment_id={exp['id']}
artifact_path={exp['artifact_path']}

必須:
- 既存成果物を前提にする
- CTAを強くする
- Telegram導線を入れる
- SNS投稿文を作る
- 次の検証指標を1つ決める
- runbook禁止
- lpgen_execで成果物化
"""

    cur = db.execute("""
        insert into router_tasks
        (
          target_bot,
          mode,
          status,
          task_text,
          created_at,
          updated_at
        )
        values
        ('ops_exec', 'EXEC', 'new', ?, datetime('now'), datetime('now'))
    """, (f"[EXEC]\nscript=run_python.sh\narg=mode=lpgen_exec;task={task_text}",))

    db.execute("""
        update revenue_experiments
        set status='improving',
            updated_at=datetime('now')
        where id=?
    """, (exp["id"],))

    db.execute("""
        insert into revenue_learnings
        (
          experiment_id,
          opportunity_id,
          learning_type,
          summary,
          evidence,
          action,
          confidence
        )
        values
        (?, ?, 'winner_candidate', '成果物生成に成功したため改善ループへ進める', ?, 'lpgen_execで改善版を作る', 75)
    """, (exp["id"], exp["opportunity_id"], exp["artifact_path"]))

    db.commit()

    print(f"improvement task created id={cur.lastrowid}")

if __name__ == "__main__":
    main()
