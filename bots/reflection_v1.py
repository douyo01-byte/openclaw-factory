from __future__ import annotations
import argparse
import sqlite3
from datetime import datetime

DB_DEFAULT = "data/openclaw.db"

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--chat-id", default="system")
    args = ap.parse_args()

    conn = connect_db(args.db)

    rows = conn.execute(
        """
        SELECT item_id, decision, score, reason, decided_at, decided_by, source
        FROM decision_events
        ORDER BY id DESC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    if not rows:
        print("Done. reflections=0 (no decision_events)")
        return

    # v1: ルールベース反省（LLM未接続）
    adopted = sum(1 for r in rows if r[1] in ("採用", "approved") or r[2] > 0)
    held    = sum(1 for r in rows if r[1] in ("保留", "hold") or r[2] == 0)
    dropped = sum(1 for r in rows if r[1] in ("見送り", "drop", "rejected") or r[2] < 0)

    top = rows[0]
    latest = f"latest: item={top[0]} decision={top[1]} score={top[2]} reason={top[3]} at={top[4]}"

    # 最小の改善提案
    actions = []
    if held > 0:
        actions.append("保留がある: 保留理由を分類して『追加調査タスク』に分解")
    if dropped > 0 and adopted == 0:
        actions.append("見送り偏重: 取得ソース/フィルタ条件を見直し（候補の質改善）")
    if adopted > 0 and dropped == 0:
        actions.append("採用偏重: 反証観点チェック（競合/実現性/法務）を追加")
    if not actions:
        actions.append("判断分布は正常: 次はTAM推定/スコアリング項目拡張")

    text = "\n".join([
        f"[reflection_v1] {datetime.now().isoformat()}",
        f"window={args.limit} adopted={adopted} held={held} dropped={dropped}",
        latest,
        "actions:",
        *[f"- {a}" for a in actions],
    ])

    conn.execute(
        "INSERT INTO retrospectives(chat_id, from_username, text) VALUES(?,?,?)",
        (args.chat_id, "system", text),
    )
    conn.commit()
    conn.close()

    print("Done. reflections=1")

if __name__ == "__main__":
    main()
