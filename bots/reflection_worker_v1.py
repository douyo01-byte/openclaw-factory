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

def build_reflection(conn: sqlite3.Connection, window_n: int) -> str:
    rows = conn.execute(
        """
        select proposal_id, title, body, created_at
        from ceo_hub_events
        where event_type='learning_result'
        order by id desc
        limit ?
        """,
        (window_n,),
    ).fetchall()
    if not rows:
        return f"[reflection_worker_v1] {datetime.now().isoformat()}\nwindow={window_n}\n(no learning_result)"
    success = sum(1 for r in rows if "result=success" in (r[2] or ""))
    neutral = sum(1 for r in rows if "result=neutral" in (r[2] or ""))
    fail = sum(1 for r in rows if "result=fail" in (r[2] or "") or "result=error" in (r[2] or ""))
    top = rows[0]
    actions = []
    if fail > 0:
        actions.append("失敗案件の共通因子を抽出して次回提案から除外")
    if success > 0:
        actions.append("success案件の語彙を decision_patterns へ反映")
    if neutral > success:
        actions.append("neutral案件は提案粒度を上げる")
    if not actions:
        actions.append("運用改善寄り success を継続")
    return "\n".join(
        [
            f"[reflection_worker_v1] {datetime.now().isoformat()}",
            f"window={window_n} success={success} neutral={neutral} fail={fail}",
            f"latest: proposal={top[0]} title={top[1]} body={top[2]} at={top[3]}",
            "actions:",
            *[f"- {a}" for a in actions],
        ]
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    conn = connect_db(args.db)
    conn.execute("create table if not exists reflection_requests(id integer primary key autoincrement, window_n integer, status text, result text, error text, processed_at text)")
    conn.execute("create table if not exists retrospectives(id integer primary key autoincrement, chat_id text, from_username text, text text, created_at text default (datetime('now')))")

    reqs = conn.execute(
        """
        select id, window_n
        from reflection_requests
        where status='new'
        order by id asc
        limit ?
        """,
        (args.limit,),
    ).fetchall()

    done = 0
    for req_id, window_n in reqs:
        try:
            result = build_reflection(conn, int(window_n))
            conn.execute(
                "insert into retrospectives(chat_id, from_username, text) values(?,?,?)",
                ("system", "system", result),
            )
            conn.execute(
                "update reflection_requests set status='done', result=?, processed_at=datetime('now') where id=?",
                (result, req_id),
            )
            done += 1
        except Exception as e:
            conn.execute(
                "update reflection_requests set status='error', error=?, processed_at=datetime('now') where id=?",
                (str(e), req_id),
            )

    conn.commit()
    conn.close()
    print(f"Done. processed={done}")

if __name__ == "__main__":
    main()
