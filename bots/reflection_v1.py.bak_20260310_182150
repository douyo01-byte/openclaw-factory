from __future__ import annotations
import argparse
import sqlite3
from datetime import datetime

DB_DEFAULT = "data/openclaw.db"

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    conn = connect_db(args.db)
    rows = conn.execute(
        """
        select proposal_id, title, body, created_at
        from ceo_hub_events
        where event_type='learning_result'
        order by id desc
        limit ?
        """,
        (args.limit,),
    ).fetchall()

    if not rows:
        print("Done. reflections=0 (no learning_result)")
        return

    success = sum(1 for r in rows if "result=success" in (r[2] or ""))
    neutral = sum(1 for r in rows if "result=neutral" in (r[2] or ""))
    fail = sum(1 for r in rows if "result=fail" in (r[2] or "") or "result=error" in (r[2] or ""))

    top = rows[0]
    latest = f"latest: proposal={top[0]} title={top[1]} body={top[2]} at={top[3]}"

    actions = []
    if fail > 0:
        actions.append("失敗案件を優先監視し、壊さない方針へ寄せる")
    if success > 0:
        actions.append("success案件の target_system / improvement_type を優先候補として再利用")
    if neutral > success:
        actions.append("中立評価が多いため、採用条件を明確化して learning_result を sharpen")
    if not actions:
        actions.append("学習分布は安定。運用改善寄りの成功パターンを継続")

    text = "\n".join(
        [
            f"[reflection_v1] {datetime.now().isoformat()}",
            f"window={args.limit} success={success} neutral={neutral} fail={fail}",
            latest,
            "actions:",
            *[f"- {a}" for a in actions],
        ]
    )

    conn.execute("create table if not exists reflection_requests(id integer primary key autoincrement, window_n integer, status text, result text, error text, processed_at text)")
    conn.execute("insert into reflection_requests(window_n,status,result) values(?,?,?)", (args.limit, "done", text))
    conn.commit()
    conn.close()
    print("Done. enqueued=1")

if __name__ == "__main__":
    main()
