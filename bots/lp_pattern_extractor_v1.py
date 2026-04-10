import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
OUT = ROOT / "data/lp_research"

BAD_WORDS = [
    "is for sale",
    "domain for sale",
    "hugedomains",
    "sedo",
    "parkingcrew",
    "buy this domain",
    "domain statistics",
    "related searches",
]

def pick_line(text, keys):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    for key in keys:
        for line in lines:
            if key in line:
                return line
    return lines[0] if lines else ""

def is_bad_text(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in BAD_WORDS)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    rows = cur.execute("""
    select id, url, niche
    from lp_sources
    where status in ('new','fetched')
    order by id asc
    limit 50
    """).fetchall()

    parsed = 0
    skipped = 0

    for source_id, url, niche in rows:
        txt_path = OUT / f"source_{source_id}.txt"
        if not txt_path.exists():
            cur.execute("update lp_sources set status=? where id=?", ("missing_text", source_id))
            skipped += 1
            continue

        text = txt_path.read_text(encoding="utf-8", errors="ignore")
        if is_bad_text(text):
            cur.execute("update lp_sources set status=? where id=?", ("bad_source", source_id))
            skipped += 1
            continue

        title = pick_line(text, ["連絡", "気持ち", "無料", "診断", "恋愛", "復縁"])
        hook = pick_line(text, ["終わる", "不安", "気持ち", "離れ", "待つ", "連絡"])
        problem = pick_line(text, ["何もしない", "不安", "迷い", "分から", "怖い"])
        promise = pick_line(text, ["整理", "確認", "分かる", "診断"])
        cta = pick_line(text, ["無料", "解放", "確認", "今すぐ"])
        price_hint = pick_line(text, ["760円", "980円", "円", "無料"])

        score = 0
        if "無料" in cta:
            score += 20
        if "円" in price_hint:
            score += 20
        if any(x in hook for x in ["終わる", "不安", "離れ", "待つ", "連絡"]):
            score += 20
        if any(x in promise for x in ["整理", "確認", "分かる", "診断"]):
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
        parsed += 1

    con.commit()
    con.close()
    print(f"lp_patterns_extracted parsed={parsed} skipped={skipped}", flush=True)

if __name__ == "__main__":
    main()
