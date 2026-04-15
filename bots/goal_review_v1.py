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
    if s is None:
        return ""
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

def related_tasks(con: sqlite3.Connection, next_action: str) -> list[sqlite3.Row]:
    q = normalize(next_action)
    rows = con.execute("""
    select id, status, mode, task_role, target_bot, task_text, reply_text, created_at, updated_at, finished_at
    from router_tasks
    where target_bot='kaikun04'
      and task_role='SYSTEM'
    order by id desc
    limit 300
    """).fetchall()
    out = []
    for r in rows:
        txt = normalize(r["task_text"] or "")
        if q and q in txt:
            out.append(r)
    return out

def judge(plan: sqlite3.Row, tasks: list[sqlite3.Row]) -> tuple[str, str, str]:
    if not tasks:
        return (
            "retry",
            normalize(plan["current_focus"]),
            normalize(plan["next_action"]),
        )

    t = tasks[0]
    status = normalize(t["status"]).lower()
    reply_text = normalize(t["reply_text"] or "")
    task_text = normalize(t["task_text"] or "")
    joined = f"{status} {reply_text} {task_text}"

    if status in {"new", "pending", "running"}:
        return (
            "keep",
            normalize(plan["current_focus"]),
            normalize(plan["next_action"]),
        )

    if status == "done":
        if re.search(r"n8n|api_server|source\+text|source +text|webhook", joined, re.I):
            return (
                "advance",
                "n8nとOpenClawの主線固定後の運用安定化へ進む",
                "api_server常駐化・n8n workflow固定・Telegram入口統合のどれが未固定かを1つだけ選び、主線をさらに細く強くする",
            )
        return (
            "advance",
            normalize(plan["current_focus"]),
            "完了した1手の結果をdocs/runtime/DBへ反映し、次に最も全体目標へ寄与する1手を再選定する",
        )

    if status in {"error", "failed", "cancelled"}:
        return (
            "retry",
            normalize(plan["current_focus"]),
            "失敗理由を1つに絞って修正し、同じnext_actionを最小差分で再実行する",
        )

    return (
        "retry",
        normalize(plan["current_focus"]),
        normalize(plan["next_action"]),
    )

def insert_plan(
    con: sqlite3.Connection,
    active_goal: str,
    current_focus: str,
    next_action: str,
    rationale: str,
    source_docs: str,
) -> int:
    cur = con.execute("""
    insert into goal_plan_state
    (active_goal, current_focus, next_action, rationale, source_docs, updated_at)
    values (?, ?, ?, ?, ?, datetime('now'))
    """, (active_goal, current_focus, next_action, rationale, source_docs))
    con.commit()
    return int(cur.lastrowid)

def main() -> None:
    con = connect()

    plan = latest_plan(con)
    if plan is None:
        print(json.dumps({"ok": False, "error": "no_goal_plan_state"}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    tasks = related_tasks(con, plan["next_action"])
    decision, next_focus, next_action = judge(plan, tasks)

    latest_task = tasks[0] if tasks else None
    rationale = " ; ".join([
        f"review_of_plan_id={plan['id']}",
        f"decision={decision}",
        f"task_count={len(tasks)}",
        f"latest_task_id={latest_task['id'] if latest_task else ''}",
        f"latest_status={normalize(latest_task['status']) if latest_task else ''}",
        f"prev_focus={normalize(plan['current_focus'])}",
        f"prev_action={normalize(plan['next_action'])}",
    ])

    new_id = insert_plan(
        con,
        active_goal=normalize(plan["active_goal"]),
        current_focus=normalize(next_focus),
        next_action=normalize(next_action),
        rationale=rationale,
        source_docs=normalize(plan["source_docs"] or "[]"),
    )

    out = {
        "ok": True,
        "decision": decision,
        "previous_plan_id": plan["id"],
        "new_plan_id": new_id,
        "latest_task": None if latest_task is None else {
            "id": latest_task["id"],
            "status": normalize(latest_task["status"]),
            "updated_at": latest_task["updated_at"],
            "finished_at": latest_task["finished_at"],
        },
        "current_focus": normalize(next_focus),
        "next_action": normalize(next_action),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    con.close()

if __name__ == "__main__":
    main()
