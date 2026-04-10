import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
OUT = ROOT / "data/lp_research"

SEEDS = [
    ("https://example.com/love1", "恋愛", "manual"),
    ("https://example.com/love2", "恋愛", "manual"),
    ("https://example.com/fukuen1", "復縁", "manual"),
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    for url, niche, source_type in SEEDS:
        cur.execute("""
        insert or ignore into lp_sources(url, niche, source_type, status)
        values(?,?,?,?)
        """, (url, niche, source_type, "new"))

    con.commit()
    con.close()
    print("lp_scout_seeded", flush=True)

if __name__ == "__main__":
    main()
