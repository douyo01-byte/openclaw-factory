from __future__ import annotations

import argparse
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from oclibs.telegram import send as tg_send

DB_DEFAULT = os.environ.get("OCLAW_DB_PATH", "./data/openclaw.db")

ROLE_ALIASES = {
    "scout": ["スカウン", "scout"],
    "japache": ["ジャパチェ", "japache"],
    "iindesuka": ["イインデスカ", "iindesuka"],
    "tanoshi": ["タノシ", "tanoshi"],
}

URL_RE = re.compile(r"(https?://\S+)")
ASK_ROLE_RE = re.compile(r"(スカウン|ジャパチェ|イインデスカ|タノシ).*(意見|見解|どう|何て|どう思)")

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def role_from_text(text: str) -> Optional[str]:
    t = (text or "").strip()
    if not t:
        return None
    for role, names in ROLE_ALIASES.items():
        for n in names:
            if n in t:
                return role
    return None

def extract_title_hint(text: str) -> str:
    t = (text or "").strip()
    t = URL_RE.sub("", t).strip()
    t = re.sub(r"\s+", " ", t)
    m = re.search(r"^(.+?)(いいね|面白|気になる|良い|微妙|高い|安い|見送り|保留|採用)", t)
    if m:
        return m.group(1).strip(" 　「」\"'")
    return t[:40].strip(" 　「」\"'")

def find_item_by_url(conn: sqlite3.Connection, url: str) -> Optional[sqlite3.Row]:
    if not url:
        return None
    return conn.execute("SELECT id, title, url FROM items WHERE url=? LIMIT 1", (url,)).fetchone()

def find_item_by_title_hint(conn: sqlite3.Connection, hint: str) -> Optional[sqlite3.Row]:
    h = (hint or "").strip()
    if len(h) < 3:
        return None
    return conn.execute(
        "SELECT id, title, url FROM items WHERE title LIKE ? ORDER BY id DESC LIMIT 1",
        (f"%{h}%",),
    ).fetchone()

def get_item_meta(conn: sqlite3.Connection, item_id: int) -> Dict[str, Any]:
    r = conn.execute(
        "SELECT item_id, priority, decision, note, updated_at FROM item_meta WHERE item_id=?",
        (item_id,),
    ).fetchone()
    if not r:
        return {"item_id": item_id, "priority": 0, "decision": "", "note": "", "updated_at": ""}
    return dict(r)

def format_meta(meta: Dict[str, Any]) -> str:
    pr = meta.get("priority", 0) or 0
    dec = (meta.get("decision", "") or "").strip() or "-"
    note = (meta.get("note", "") or "").replace("\n", " / ").strip()
    if len(note) > 120:
        note = note[:120] + "…"
    if note:
        return f"[meta] prio={pr} decision={dec} note={note}"
    return f"[meta] prio={pr} decision={dec}"

def strip_role_words(text: str) -> str:
    t = (text or "").strip()
    for names in ROLE_ALIASES.values():
        for n in names:
            t = t.replace(n, "")
    t = t.replace("の意見は？", "").replace("意見は？", "").replace("意見は", "")
    t = t.replace("見解は？", "").replace("見解は", "")
    return t.strip()

def build_role_reply(role: Optional[str]) -> Tuple[str, str]:
    if role == "japache":
        head = "🕵️ ジャパチェ"
        body = "国内上陸の兆候を先に確認する。日本語LP、代理店表記、Amazon/楽天/BASE、プレスリリースをチェック。なければ連絡先回収へ。"
        return head, body
    if role == "scout":
        head = "🌍 スカウン"
        body = "ローンチ直後は公式サイトのContactが見つかりやすい。/contact /about /privacy を先に当てる。なければSNSやドメイン情報へ。"
        return head, body
    if role == "iindesuka":
        head = "💰 イインデスカ"
        body = "単価×輸送×差別化で即死判定。サイズ・重量・破損率・関税・返品コストをざっくりでも出して落とす。"
        return head, body
    if role == "tanoshi":
        head = "🔥 タノシ"
        body = "初手はテスト輸入→反応→独占提案の順。連絡先が取れたら返事が来やすい短文で刺す。"
        return head, body
    head = "🧠 ヤルデ"
    body = "誰の意見が欲しい？ ジャパチェ/スカウン/イインデスカ/タノシ を文中に入れて投げて。"
    return head, body

def resolve_item(conn: sqlite3.Connection, text: str) -> Optional[sqlite3.Row]:
    urls = URL_RE.findall(text or "")
    if urls:
        it = find_item_by_url(conn, urls[0])
        if it:
            return it
    hint = extract_title_hint(text)
    return find_item_by_title_hint(conn, hint)

def handle_chat(conn: sqlite3.Connection, row: sqlite3.Row) -> Tuple[str, Optional[str]]:
    cmd_id = row["id"]
    chat_id = str(row["chat_id"])
    text = (row["text"] or "").strip()

    if not text:
        return ("ignored", None)
    if text.startswith("/"):
        return ("ignored", None)

    role = role_from_text(text)
    item = resolve_item(conn, text)

    head, body = build_role_reply(role)

    if item:
        try:
            conn.execute(
                "INSERT INTO chat_jobs(chat_id, item_id, role, query, status, created_at, updated_at) VALUES(?,?,?,?, 'new', datetime('now'), datetime('now'))",
                (chat_id, int(item["id"]), role or "", text, ),
            )
            conn.commit()
        except Exception:
            pass
        meta = get_item_meta(conn, int(item["id"]))
        reply = (
            f"{head}\n"
            f"{format_meta(meta)}\n"
            f"対象: {item['title']}\n"
            f"{item['url']}\n\n"
            f"{body}"
        )
    else:
        q = strip_role_words(text)
        reply = (
            f"{head}\n"
            f"対象候補: {q}\n\n"
            f"{body}"
        )

    tg_send(reply)
    return ("chatted", None)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    conn = connect_db(args.db)

    rows = conn.execute(
        "SELECT id, chat_id, message_id, text FROM inbox_commands WHERE status='new' ORDER BY id ASC LIMIT ?",
        (args.limit,),
    ).fetchall()

    chatted = 0
    ignored = 0

    for r in rows:
        status, error = handle_chat(conn, r)
        if status == "chatted":
            chatted += 1
            conn.execute(
                "UPDATE inbox_commands SET status=?, applied_at=datetime('now'), error=? WHERE id=?",
                ("chatted", error, r["id"]),
            )
        else:
            ignored += 1
            conn.execute(
                "UPDATE inbox_commands SET status=?, applied_at=datetime('now'), error=? WHERE id=?",
                ("ignored", error, r["id"]),
            )

    conn.commit()
    conn.close()
    print(f"Done. chatted={chatted} ignored={ignored}")

if __name__ == "__main__":
    main()
