from __future__ import annotations
import argparse
import sqlite3
from datetime import datetime

DB_DEFAULT = "data/openclaw.db"

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def build_reflection(conn: sqlite3.Connection, window_n: int) -> str:
    rows = conn.execute(
        """
        SELECT item_id, decision, score, reason, decided_at, decided_by, source
        FROM decision_events
        ORDER BY id DESC
        LIMIT ?
        """,
        (window_n,),
    ).fetchall()

    if not rows:
        return f"[reflection_worker_v1] {datetime.now().isoformat()}\nwindow={window_n}\n(no decision_events)"

    adopted = sum(1 for r in rows if r[2] > 0)
    held    = sum(1 for r in rows if r[2] == 0)
    dropped = sum(1 for r in rows if r[2] < 0)

    top = rows[0]
    latest = f"latest: item={top[0]} decision={top[1]} score={top[2]} reason={top[3]} at={top[4]}"

    actions = []
    if held > 0:
        actions.append("保留理由をタグ化→追加調査タスクへ分解")
    if dropped > 0 and adopted == 0:
        actions.append("見送り偏重: ソース/フィルタを見直し、候補品質改善")
    if adopted > 0 and dropped == 0:
        actions.append("採用偏重: 反証観点（競合/実現性/法務）チェック追加")
    if not actions:
        actions.append("判断分布は正常: 次はTAM推定/スコア項目拡張")

    return "\n".join([
        f"[reflection_worker_v1] {datetime.now().isoformat()}",
        f"window={window_n} adopted={adopted} held={held} dropped={dropped}",
        latest,
        "actions:",
        *[f"- {a}" for a in actions],
    ])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--limit", type=int, default=10)  # 1回で処理する件数
    args = ap.parse_args()

    conn = connect_db(args.db)

    reqs = conn.execute(
        """
        SELECT id, window_n
        FROM reflection_requests
        WHERE status='new'
        ORDER BY id ASC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    done = 0
    for req_id, window_n in reqs:
        try:
            result = build_reflection(conn, int(window_n))
            conn.execute(
                "INSERT INTO retrospectives(chat_id, from_username, text) VALUES(?,?,?)",
                ("system", "system", result),
            )
            conn.execute(
                "UPDATE reflection_requests SET status='done', result=?, processed_at=datetime('now') WHERE id=?",
                (result, req_id),
            )
            done += 1
        except Exception as e:
            conn.execute(
                "UPDATE reflection_requests SET status='error', error=?, processed_at=datetime('now') WHERE id=?",
                (str(e), req_id),
            )

    conn.commit()
    conn.close()

    print(f"Done. processed={done}")

if __name__ == "__main__":
    main()
