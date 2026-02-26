import sqlite3
from dataclasses import dataclass
from typing import List, Optional
from oclibs.telegram import send as tg_send

DB_PATH = "data/openclaw.db"

@dataclass
class Row:
    id: int
    title: str
    url: str
    source: str
    status: str
    first_seen_at: str

def fetch_pool(limit: int = 60) -> List[Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # status='new' を優先。無ければ全部から引く。
    rows = cur.execute("""
        SELECT id, title, url, source, status, first_seen_at
        FROM items
        WHERE status IN ('new','shortlisted','review')
        ORDER BY
          CASE status WHEN 'new' THEN 0 WHEN 'review' THEN 1 WHEN 'shortlisted' THEN 2 ELSE 9 END,
          id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        rows = cur.execute("""
            SELECT id, title, url, source, status, first_seen_at
            FROM items
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    conn.close()
    return [Row(**dict(r)) for r in rows]

def pick_top(rows: List[Row], k: int = 10) -> List[Row]:
    # いまは最短のため「新しい順」。後でスコアリング/キャラ学習に差し替えOK。
    return rows[:k]

def mark_status(item_ids: List[int], new_status: str = "review"):
    if not item_ids:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany("UPDATE items SET status=? WHERE id=?", [(new_status, i) for i in item_ids])
    conn.commit()
    conn.close()

def meeting_text(top: List[Row]) -> str:
    lines = []
    lines.append("ヤルデ（20代の天才/総括）\n🧠 会議開始。目的：DBに溜めた候補から“今日の当たり”を絞る。\n")
    lines.append("スカウン（さすらいの旅人/30代）\n……倉庫（DB）から新しめの候補を持ってきた。まずは並べる。\n")
    lines.append("ジャパチェ（市場調査/50代）\n日本で既に売ってそうな匂いがするやつは外すぞ。\n")
    lines.append("イインデスカ（利益判定/50代）\n家電・ガジェット寄り優先。薄利は落とすわ。\n")

    for i, r in enumerate(top, 1):
        lines.append(f"【候補{i}】({r.source}) status={r.status}\n{r.title}\n{r.url}\n")

    lines.append("タノシ（熱血営業/40代）\nよっしゃ！次は“公式サイトの連絡先だけ”抜いて、勝ち筋を作るぞ！\n")
    lines.append("ヤルデ（20代の天才/総括）\n✅ 本日の結論：この10件を review 扱いに更新。次回会議でさらに絞る。\n")
    return "\n".join(lines)

def main():
    pool = fetch_pool(limit=60)
    top = pick_top(pool, k=10)
    mark_status([r.id for r in top], new_status="review")
    msg = meeting_text(top)
    tg_send(msg)
    print("Sent meeting_from_db_v1:", len(top))

if __name__ == "__main__":
    main()
