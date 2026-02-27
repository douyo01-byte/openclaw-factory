from __future__ import annotations

import argparse
import os
import sqlite3
import time
from typing import Any, Dict, Optional

from oclibs.tg_api import get_updates

DB_DEFAULT = "data/openclaw.db"

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def ensure_state_table(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bot_state (
      k TEXT PRIMARY KEY,
      v TEXT
    )
    """)
    conn.commit()

def load_offset(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT v FROM bot_state WHERE k='tg_offset'")
    row = cur.fetchone()
    return int(row[0]) if row else 0

def save_offset(conn: sqlite3.Connection, offset: int):
    conn.execute("INSERT INTO bot_state(k,v) VALUES('tg_offset', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(offset),))
    conn.commit()

def extract_user(u: Dict[str, Any]) -> tuple[str, str]:
    username = u.get("username") or ""
    name = " ".join([p for p in [u.get("first_name"), u.get("last_name")] if p]) or u.get("name") or ""
    return username, name

def insert_command(conn: sqlite3.Connection, chat_id: str, msg: Dict[str, Any]):
    message_id = msg.get("message_id")
    text = (msg.get("text") or "").strip()
    if not text:
        return

    frm = msg.get("from") or {}
    username, name = extract_user(frm)

    reply_to = msg.get("reply_to_message") or {}
    reply_to_id = reply_to.get("message_id")

    conn.execute(
        """
        INSERT INTO inbox_commands(chat_id, message_id, reply_to_message_id, from_username, from_name, text)
        VALUES(?,?,?,?,?,?)
        """,
        (str(chat_id), message_id, reply_to_id, username, name, text),
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--once", action="store_true", help="poll once and exit")
    args = ap.parse_args()

    conn = connect_db(args.db)
    ensure_state_table(conn)

    offset = load_offset(conn)
    print("tg_inbox_poll_v1 started. offset=", offset)

    while True:
        try:
            data = get_updates(offset=offset, timeout=50)
            ok = data.get("ok")
            if not ok:
                time.sleep(2)
                continue

            results = data.get("result") or []
            for upd in results:
                update_id = upd.get("update_id")
                if update_id is None:
                    continue

                # message or edited_message or channel_post… とりあえず message を拾う
                msg = upd.get("message") or upd.get("edited_message")
                if msg:
                    chat = msg.get("chat") or {}
                    chat_id = chat.get("id")
                    if chat_id is not None:
                        insert_command(conn, str(chat_id), msg)
                        conn.commit()

                # Telegram仕様：次回は update_id+1 をoffsetにする
                offset = max(offset, update_id + 1)

            save_offset(conn, offset)

            if args.once:
                print("once done. offset=", offset, "updates=", len(results))
                break

            time.sleep(args.sleep)

        except KeyboardInterrupt:
            print("stopped by user")
            break
        except Exception as e:
            # ネットワーク瞬断を想定して落ちない
            print("poll error:", type(e).__name__, e)
            time.sleep(3)

    conn.close()

if __name__ == "__main__":
    main()
