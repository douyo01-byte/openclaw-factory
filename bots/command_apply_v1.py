from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import datetime

DB_DEFAULT = "data/openclaw.db"

CMD_PAT = re.compile(r"^/(approve|reject|hold|prio|note|retro)\b(.*)$", re.I)

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def parse_item_id(s: str) -> tuple[int | None, str]:
    s = s.strip()
    m = re.match(r"^(\d+)\b(.*)$", s)
    if not m:
        return None, s
    return int(m.group(1)), (m.group(2) or "").strip()

def upsert_item_meta(conn: sqlite3.Connection, item_id: int):
    conn.execute("INSERT OR IGNORE INTO item_meta(item_id) VALUES(?)", (item_id,))

def set_decision(conn: sqlite3.Connection, item_id: int, decision: str, note: str | None = None):
    upsert_item_meta(conn, item_id)
    conn.execute(
        "UPDATE item_meta SET decision=?, updated_at=datetime('now') WHERE item_id=?",
        (decision, item_id),
    )
    if note:
        conn.execute(
            "UPDATE item_meta SET note=COALESCE(note,'') || CASE WHEN note IS NULL OR note='' THEN '' ELSE '\n' END || ?, updated_at=datetime('now') WHERE item_id=?",
            (note, item_id),
        )

def set_priority(conn: sqlite3.Connection, item_id: int, prio: int):
    prio = max(0, min(100, prio))
    upsert_item_meta(conn, item_id)
    conn.execute(
        "UPDATE item_meta SET priority=?, updated_at=datetime('now') WHERE item_id=?",
        (prio, item_id),
    )

def add_note(conn: sqlite3.Connection, item_id: int, note: str):
    upsert_item_meta(conn, item_id)
    conn.execute(
        "UPDATE item_meta SET note=COALESCE(note,'') || CASE WHEN note IS NULL OR note='' THEN '' ELSE '\n' END || ?, updated_at=datetime('now') WHERE item_id=?",
        (note, item_id),
    )

def insert_retro(conn: sqlite3.Connection, chat_id: str, from_username: str | None, text: str):
    conn.execute(
        "INSERT INTO retrospectives(chat_id, from_username, text) VALUES(?,?,?)",
        (chat_id, from_username or "", text),
    )

def apply_one(conn: sqlite3.Connection, row) -> tuple[str, str | None]:
    """
    returns: (status, error)
    """
    cmd_id, chat_id, from_username, text = row
    text = (text or "").strip()

    m = CMD_PAT.match(text)
    if not m:
        return ("ignored", None)

    cmd = m.group(1).lower()
    rest = (m.group(2) or "").strip()

    if cmd == "retro":
        if not rest:
            return ("error", "retro requires text")
        insert_retro(conn, chat_id=str(chat_id), from_username=from_username, text=rest)
        return ("applied", None)

    item_id, tail = parse_item_id(rest)
    if item_id is None:
        return ("error", f"{cmd} requires item_id (e.g. /{cmd} 31 ...)")

    if cmd == "approve":
        set_decision(conn, item_id, "approved", note=tail or None)
        return ("applied", None)
    if cmd == "reject":
        set_decision(conn, item_id, "rejected", note=tail or None)
        return ("applied", None)
    if cmd == "hold":
        set_decision(conn, item_id, "hold", note=tail or None)
        return ("applied", None)
    if cmd == "prio":
        if not tail:
            return ("error", "prio requires number 0-100 (e.g. /prio 31 80)")
        try:
            pr = int(tail.split()[0])
        except Exception:
            return ("error", "prio parse failed (need integer)")
        set_priority(conn, item_id, pr)
        return ("applied", None)
    if cmd == "note":
        if not tail:
            return ("error", "note requires text (e.g. /note 31 ...)")
        add_note(conn, item_id, tail)
        return ("applied", None)

    return ("ignored", None)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    conn = connect_db(args.db)

    rows = conn.execute(
        """
        SELECT id, chat_id, from_username, text
        FROM inbox_commands
        WHERE status='new'
        ORDER BY id ASC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    applied = 0
    ignored = 0
    err = 0

    for r in rows:
        cmd_id = r[0]
        status, error = apply_one(conn, r)
        if status == "applied":
            applied += 1
        elif status == "ignored":
            ignored += 1
        else:
            err += 1

        conn.execute(
            "UPDATE inbox_commands SET status=?, applied_at=datetime('now'), error=? WHERE id=?",
            (status, error, cmd_id),
        )

    conn.commit()
    conn.close()

    print(f"Done. applied={applied} ignored={ignored} error={err}")

if __name__ == "__main__":
    main()
