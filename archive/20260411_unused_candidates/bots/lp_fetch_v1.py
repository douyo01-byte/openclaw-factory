import os
import re
import sqlite3
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
OUT = ROOT / "data/lp_research"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"
}

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def main():
    OUT.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    rows = cur.execute("""
    select id, url, niche
    from lp_sources
    where status='new'
    order by id asc
    limit 20
    """).fetchall()

    done = 0
    fail = 0

    for source_id, url, niche in rows:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            html = r.text
            text = html_to_text(html)

            html_path = OUT / f"source_{source_id}.html"
            text_path = OUT / f"source_{source_id}.txt"
            html_path.write_text(html, encoding="utf-8")
            text_path.write_text(text, encoding="utf-8")

            title = ""
            m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()

            cur.execute("""
            insert into lp_pages(source_id, url, title, raw_text, html_path, text_path)
            values(?,?,?,?,?,?)
            """, (
                source_id,
                url,
                title,
                text[:200000],
                str(html_path),
                str(text_path),
            ))

            cur.execute("""
            update lp_sources
            set status='fetched', fetched_at=datetime('now')
            where id=?
            """, (source_id,))
            done += 1
        except Exception as e:
            cur.execute("""
            update lp_sources
            set status=?
            where id=?
            """, (f"fetch_error:{type(e).__name__}", source_id))
            fail += 1

    con.commit()
    con.close()
    print(f"lp_fetch_done={done} fail={fail}", flush=True)

if __name__ == "__main__":
    main()
