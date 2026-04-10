import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
OUT = ROOT / "data/lp_research"

MOCK_TEXT = """連絡するべきか、待つべきか。
このまま何もしなければ関係は終わるかもしれません。
今の恋愛状況を30秒で整理します。
無料で現状を確認できます。
続きを760円で解放。
"""

def pick_line(text, keys):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    for key in keys:
        for line in lines:
            if key in line:
                return line
    return lines[0] if lines else ""

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    rows = cur.execute("""
    select id, url, niche
    from lp_sources
    where status in ('new','fetched')
    order by id asc
    limit 20
    """).fetchall()

    for source_id, url, niche in rows:
        txt_path = OUT / f"source_{source_id}.txt"
        if not txt_path.exists():
            txt_path.write_text(MOCK_TEXT, encoding="utf-8")

        text = txt_path.read_text(encoding="utf-8", errors="ignore")

        title = pick_line(text, ["連絡", "気持ち", "無料", "診断"])
        hook = pick_line(text, ["終わる", "不安", "気持ち"])
        problem = pick_line(text, ["何もしなければ", "不安", "迷い"])
        promise = pick_line(text, ["整理", "確認", "分かる"])
        cta = pick_line(text, ["無料", "解放", "確認"])
        price_hint = pick_line(text, ["760円", "無料", "円"])

        cur.execute("""
        insert into lp_pages(source_id, url, title, raw_text, text_path)
        values(?,?,?,?,?)
        """, (source_id, url, title, text, str(txt_path)))

        score = 0
        if "無料" in cta:
            score += 20
        if "760円" in price_hint:
            score += 20
        if "終わる" in hook or "不安" in hook:
            score += 20

        cur.execute("""
        insert into lp_patterns
        (source_id, hook, problem, promise, proof, cta, price_hint, notes, score)
        values(?,?,?,?,?,?,?,?,?)
        """, (
            source_id,
            hook,
            problem,
            promise,
            "",
            cta,
            price_hint,
            f"niche={niche}",
            score
        ))

        cur.execute("""
        update lp_sources
        set status='parsed', fetched_at=datetime('now')
        where id=?
        """, (source_id,))

    con.commit()
    con.close()
    print("lp_patterns_extracted", flush=True)

if __name__ == "__main__":
    main()
