from __future__ import annotations
import json
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))

def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("pragma journal_mode=WAL")
    con.execute("pragma busy_timeout=5000")
    return con

def normalize(s: str) -> str:
    s = s.replace("\u3000", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def latest_plan(con: sqlite3.Connection) -> sqlite3.Row | None:
    return con.execute("""
    select id, active_goal, current_focus, next_action, rationale, source_docs, updated_at
    from goal_plan_state
    order by id desc
    limit 1
    """).fetchone()

def find_duplicate_task(con: sqlite3.Connection, next_action: str) -> sqlite3.Row | None:
    q = normalize(next_action)
    rows = con.execute("""
    select id, status, task_text, created_at, updated_at
    from router_tasks
    where target_bot='kaikun04'
      and task_role='SYSTEM'
      and status in ('new','pending','running','done')
    order by id desc
    limit 200
    """).fetchall()

    for r in rows:
        txt = normalize(r["task_text"] or "")
        if q and q in txt:
            return r
    return None

def build_task_text(plan: sqlite3.Row) -> str:
    active_goal = normalize(plan["active_goal"] or "")
    current_focus = normalize(plan["current_focus"] or "")
    next_action = normalize(plan["next_action"] or "")
    rationale = normalize(plan["rationale"] or "")
    source_docs = normalize(plan["source_docs"] or "")

    return f"""[GOAL_PLAN]
plan_id={plan["id"]}
active_goal={active_goal}
current_focus={current_focus}
next_action={next_action}
rationale={rationale}
source_docs={source_docs}

指示:
- 全体目標への寄与が最大の1手だけ進める
- 反応型ではなく計画駆動で考える
- まず next_action を達成する最小の実装/修正/確認を提案または実行案に落とす
- 不要な横展開はしない
""".strip()

def insert_router_task(con: sqlite3.Connection, plan: sqlite3.Row, task_text: str) -> int:
    cur = con.execute("""
    insert into router_tasks
    (
      source_command_id,
      parent_task_id,
      task_role,
      target_bot,
      mode,
      status,
      task_text,
      created_at,
      updated_at
    )
    values
    (
      null,
      null,
      'SYSTEM',
      'kaikun04',
      'THINK',
      'new',
      ?,
      datetime('now'),
      datetime('now')
    )
    """, (task_text,))
    con.commit()
    return int(cur.lastrowid)

def main() -> None:
    con = connect()

    plan = latest_plan(con)
    if plan is None:
        print(json.dumps({"ok": False, "error": "no_goal_plan_state"}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    dup = find_duplicate_task(con, plan["next_action"])
    if dup is not None:
        print(json.dumps({
            "ok": True,
            "inserted": False,
            "reason": "duplicate_next_action",
            "plan_id": plan["id"],
            "existing_router_task_id": dup["id"],
            "existing_status": dup["status"],
            "next_action": normalize(plan["next_action"]),
        }, ensure_ascii=False, indent=2))
        return

    task_text = build_task_text(plan)
    new_id = insert_router_task(con, plan, task_text)

    print(json.dumps({
        "ok": True,
        "inserted": True,
        "plan_id": plan["id"],
        "router_task_id": new_id,
        "next_action": normalize(plan["next_action"]),
    }, ensure_ascii=False, indent=2))

    con.close()

if __name__ == "__main__":
    main()
