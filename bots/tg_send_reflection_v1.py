from __future__ import annotations

import argparse
import sqlite3

DB_DEFAULT = "data/openclaw.db"

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    args = ap.parse_args()

    conn = connect_db(args.db)
    row = conn.execute(
        """
        SELECT id, text
        FROM retrospectives
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()

    if not row:
        print("Done. sent=0 (no retrospectives)")
        return

    _id, text = row

    from oclibs.telegram import send as tg_send
    tg_send(text)

    print(f"Done. sent=1 id={_id}")

if __name__ == "__main__":
    main()
