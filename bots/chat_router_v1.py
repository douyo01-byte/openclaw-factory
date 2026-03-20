from __future__ import annotations

import argparse
import os
import re
import sqlite3


def _normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\s+", " ", s).strip()
    jp = r"\u3040-\u30ff\u4e00-\u9fff"
    s = re.sub(rf"(?<=[{jp}])\s+(?=[{jp}])", "", s)
    s = s.replace("＃", "#")
    return s

def enqueue_chat_job(conn, chat_id, item_id, role, query):
    conn.execute(
        "insert into chat_jobs(chat_id,item_id,role,query,status) values(?,?,?,?, 'new')",
        (str(chat_id), item_id, role, query),
    )
    conn.commit()

def set_ctx_last_item(conn, chat_id, item_id):
    conn.execute(
        "INSERT INTO bot_state(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (f"ctx:last_item:{chat_id}", str(item_id)),
    )
    conn.commit()


from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from oclibs.telegram import send as tg_send

from bots.dev_approval_parser import parse_approval
from bots.dev_executor_v1 import main as create_pr

DB_DEFAULT = os.environ.get("OCLAW_DB_PATH", "./data/openclaw.db")

ROLE_ALIASES = {
    "scout": ["スカウン", "scout"],
    "japache": ["ジャパチェ", "japache"],
    "iindesuka": ["イインデスカ", "iindesuka"],
    "tanoshi": ["タノシ", "tanoshi"],
}

URL_RE = re.compile(r"(https?://\S+)")
ASK_ROLE_RE = re.compile(
    r"(スカウン|ジャパチェ|イインデスカ|タノシ).*(意見|見解|どう|何て|どう思)"
)


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
    m = re.search(
        r"^(.+?)(いいね|面白|気になる|良い|微妙|高い|安い|見送り|保留|採用)", t
    )
    if m:
        return m.group(1).strip(" 　「」\"'")
    return t[:40].strip(" 　「」\"'")


def find_item_by_url(conn: sqlite3.Connection, url: str) -> Optional[sqlite3.Row]:
    if not url:
        return None
    return conn.execute(
        "SELECT id, title, url FROM items WHERE url=? LIMIT 1", (url,)
    ).fetchone()


def find_item_by_title_hint(
    conn: sqlite3.Connection, hint: str
) -> Optional[sqlite3.Row]:
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
        return {
            "item_id": item_id,
            "priority": 0,
            "decision": "",
            "note": "",
            "updated_at": "",
        }
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



def normalize_chat_query(text: str) -> str:
    q = strip_role_words(text)
    q = re.sub(r"\s+", " ", (q or "").strip())
    return q

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


def parse_decision(text: str):
    t = (text or "").strip()
    if not t:
        return None
    a = t.split(None, 1)
    k = a[0]
    if k not in ("採用", "保留", "見送り"):
        return None
    r = (a[1] if len(a) > 1 else "").strip()
    return (k, r)


def insert_decision_event(
    conn,
    item_id: int,
    decision: str,
    score: int,
    reason: str,
    decided_by: str = "tg",
    source: str = "tg",
) -> None:
    conn.execute(
        "INSERT INTO decision_events(item_id, decision, score, reason, decided_by, source) VALUES(?,?,?,?,?,?)",
        (item_id, decision, score, (reason or "").strip(), decided_by, source),
    )


def upsert_decision_reason(conn, item_id: int, reason: str) -> None:
    conn.execute(
        "INSERT INTO decision_reason(item_id, reason, updated_at) VALUES(?,?,datetime('now')) "
        "ON CONFLICT(item_id) DO UPDATE SET reason=excluded.reason, updated_at=datetime('now')",
        (int(item_id), (reason or "").strip()),
    )
    conn.commit()


def apply_chat_decision(conn: sqlite3.Connection, chat_id: str, decision: str, reason: str) -> bool:
    r = conn.execute(
        "SELECT v FROM bot_state WHERE k=? LIMIT 1", (f"ctx:last_item:{chat_id}",)
    ).fetchone()
    if not (r and str(r["v"]).strip()):
        return False
    item_id = int(r["v"])
    full_reason = f"{decision} {reason}".strip()
    upsert_decision_reason(conn, item_id, full_reason)
    score = 1 if decision == "採 用 " else 0 if decision == "保 留 " else -1 if decision == "見 送 り" else 0
    insert_decision_event(
        conn, item_id, decision, score, reason, decided_by="tg", source="tg"
    )
    tg_send(full_reason)
    return True


def resolve_item(conn: sqlite3.Connection, text: str) -> Optional[sqlite3.Row]:
    urls = URL_RE.findall(text or "")
    if urls:
        it = find_item_by_url(conn, urls[0])
        if it:
            return it
    hint = extract_title_hint(text)
    return find_item_by_title_hint(conn, hint)


def get_item(conn, item_id):
    return conn.execute(
        "SELECT id,title,url FROM items WHERE id=? LIMIT 1", (item_id,)
    ).fetchone()

def resolve_item_with_context(conn: sqlite3.Connection, chat_id: str, text: str):
    item = resolve_item(conn, text)
    q = normalize_chat_query(text)
    if not item:
        hint = (
            extract_title_hint(text)
            or extract_title_hint(q)
            or (q.split()[0] if q else "")
        )
        item = find_item_by_title_hint(conn, hint) if hint else None
    if not item:
        r = conn.execute(
            "SELECT v FROM bot_state WHERE k=? LIMIT 1", (f"ctx:last_item:{chat_id}",)
        ).fetchone()
        item = get_item(conn, int(r["v"])) if r and str(r["v"]).strip() else None
    return item, q


def build_chat_reply(
    conn: sqlite3.Connection,
    role: Optional[str],
    item: Optional[sqlite3.Row],
    q: str,
) -> str:
    reply = build_chat_reply(conn, role, item, q)
    tg_send(reply)
    if item:
        set_ctx_last_item(conn, row["chat_id"], int(item["id"]))
        enqueue_chat_job(
            conn, row["chat_id"], int(item["id"]), role or "", normalize_chat_query(text)
        )
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
        txt = _normalize_text(r["text"])
        r2 = {"id": r["id"], "chat_id": r["chat_id"], "message_id": r["message_id"], "text": txt}
        status, error = handle_chat(conn, r2)

        dev_id = parse_approval(txt)

        if dev_id is not None:

            try:

                ok = create_pr(dev_id)

                if ok:

                    conn.execute(
                        "UPDATE inbox_commands SET status=?, applied_at=datetime('now'), error=? WHERE id=?",
                        ("applied", None, r["id"]),
                    )

                else:

                    conn.execute(
                        "UPDATE inbox_commands SET status=?, applied_at=datetime('now'), error=? WHERE id=?",
                        ("error", "proposal_not_found", r["id"]),
                    )

            except Exception as e:

                conn.execute(
                    "UPDATE inbox_commands SET status=?, applied_at=datetime('now'), error=? WHERE id=?",
                    ("error", str(e)[:500], r["id"]),
                )

            conn.commit()

            continue
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
