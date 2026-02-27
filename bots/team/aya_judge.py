from __future__ import annotations

import argparse
import os

def _load_persona():
  core=os.environ.get("CORE_PERSONA_FILE")
  role=os.environ.get("PERSONA_FILE")
  t=[]
  if core and os.path.exists(core):
    t.append(open(core,"r",encoding="utf-8").read().strip())
  if role and os.path.exists(role):
    t.append(open(role,"r",encoding="utf-8").read().strip())
  return "\n\n".join([x for x in t if x])

PERSONA=_load_persona()
past_decisions=brain.recall_decisions()
success_patterns=brain.recall_success_patterns()
decision_patterns=brain.recall_decision_patterns()
PERSONA=PERSONA+("\n\n過去の決定(直近):\n"+past_decisions if past_decisions else "")+("\n\n成功パターン:\n"+success_patterns if success_patterns else "")+("\n\n判断パターン重み:\n"+decision_patterns if decision_patterns else "")

import re

INTUITIVE_DECISION_RE = re.compile(r'^(A|D|H)\s+(\d+)\s*(.*)$', re.IGNORECASE)
INTUITIVE_PRIO_RE     = re.compile(r'^P(\d{1,3})\s+(\d+)\s*(.*)$', re.IGNORECASE)

def insert_decision_event(conn, item_id: int, decision: str, score: int, reason: str, decided_by: str='tg', source: str='tg'):
    conn.execute(
        "INSERT INTO decision_events(item_id, decision, score, reason, decided_by, source) VALUES(?,?,?,?,?,?)",
        (item_id, decision, score, (reason or '').strip(), decided_by, source)
    )

def upsert_decision_reason(conn, item_id: int, reason: str):
    conn.execute("INSERT INTO decision_reason(item_id, reason, updated_at) VALUES(?,?,datetime('now')) ON CONFLICT(item_id) DO UPDATE SET reason=excluded.reason, updated_at=datetime('now')", (item_id, (reason or '').strip()))

def try_apply_intuitive(conn, text: str) -> bool:
    t = (text or '').strip()
    if not t:
        return False
    m = INTUITIVE_DECISION_RE.match(t)
    if m:
        code = m.group(1).upper()
        item_id = int(m.group(2))
        reason = (m.group(3) or '').strip()
        decision = {'A':'approved','D':'drop','H':'hold'}[code]
        set_decision(conn, item_id, decision, note=(reason or None))
        if reason:
            upsert_decision_reason(conn, item_id, reason)
            d=(reason or '').strip().split(' ',1)
            decision=d[0] if d else ''
            rest=d[1] if len(d)>1 else ''
            score = 1 if decision=='採用' else 0 if decision=='保留' else -1 if decision=='見送り' else 0
            insert_decision_event(conn, item_id, decision, score, rest, decided_by='tg', source='tg')
        return True
    m = INTUITIVE_PRIO_RE.match(t)
    if m:
        pr = int(m.group(1))
        item_id = int(m.group(2))
        note = (m.group(3) or '').strip()
        pr = max(0, min(100, pr))
        set_priority(conn, item_id, pr)
        if note:
            add_note(conn, item_id, note)
        return True
    return False

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
    if try_apply_intuitive(conn, text):
        return ('applied', None)
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
    if try_apply_intuitive(conn, text):
        return ('applied', None)
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
