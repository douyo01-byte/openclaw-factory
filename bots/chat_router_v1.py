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


def fetch_item_by_url_row(conn: sqlite3.Connection, url: str):
    return conn.execute(
        "SELECT id, title, url FROM items WHERE url=? LIMIT 1",
        (url,),
    ).fetchone()


def find_item_by_url(conn: sqlite3.Connection, url: str) -> Optional[sqlite3.Row]:
    if not url:
        return None
    return fetch_item_by_url_row(conn, url)


def fetch_item_by_title_hint_row(conn: sqlite3.Connection, hint: str):
    return conn.execute(
        "SELECT id, title, url FROM items WHERE title LIKE ? ORDER BY id DESC LIMIT 1",
        (f"%{hint}%",),
    ).fetchone()


def find_item_by_title_hint(
    conn: sqlite3.Connection, hint: str
) -> Optional[sqlite3.Row]:
    h = (hint or "").strip()
    if len(h) < 3:
        return None
    return fetch_item_by_title_hint_row(conn, h)


def fetch_item_meta_row(conn: sqlite3.Connection, item_id: int):
    return conn.execute(
        "SELECT item_id, priority, decision, note, updated_at FROM item_meta WHERE item_id=?",
        (item_id,),
    ).fetchone()


def fetch_bot_state_value(conn: sqlite3.Connection, key: str):
    row = conn.execute(
        "SELECT v FROM bot_state WHERE k=? LIMIT 1",
        (key,),
    ).fetchone()
    return row["v"] if row and row["v"] is not None else None


def get_item_meta(conn: sqlite3.Connection, item_id: int) -> Dict[str, Any]:
    r = fetch_item_meta_row(conn, item_id)
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

def build_japache_role_reply() -> Tuple[str, str]:
    head = "🕵️ ジ ャ パ チ ェ "
    body = "国 内 上 陸 の 兆 候 を 先 に 確 認 す る 。 日 本 語 LP、 代 理 店 表 記 、 Amazon/楽 天 /BASE、 プ レ ス リ リ ー ス を チ ェ ッ ク 。 な け れ ば 連 絡 先 回 収 へ 。 "
    return head, body

def build_scout_role_reply() -> Tuple[str, str]:
    head = "🌍 ス カ ウ ン "
    body = "ロ ー ン チ 直 後 は 公 式 サ イ ト の Contactが 見 つ か り や す い 。 /contact /about /privacy を 先 に 当 て る 。 な け れ ば SNSや ド メ イ ン 情 報 へ 。 "
    return head, body

def build_iindesuka_role_reply() -> Tuple[str, str]:
    head = "💰 イ イ ン デ ス カ "
    body = "単 価 ×輸 送 ×差 別 化 で 即 死 判 定 。 サ イ ズ ・ 重 量 ・ 破 損 率 ・ 関 税 ・ 返 品 コ ス ト を ざ っ く り で も 出 し て 落 と す 。 "
    return head, body

def build_tanoshi_role_reply() -> Tuple[str, str]:
    head = "🔥 タ ノ シ "
    body = "初 手 は テ ス ト 輸 入 →反 応 →独 占 提 案 の 順 。 連 絡 先 が 取 れ た ら 返 事 が 来 や す い 短 文 で 刺 す 。 "
    return head, body


def build_yarude_role_reply() -> Tuple[str, str]:
    head = "🧠 ヤ ル デ "
    body = "誰 の 意 見 が 欲 し い ？  ジ ャ パ チ ェ /ス カ ウ ン /イ イ ン デ ス カ /タ ノ シ  を 文中 に 入 れ て 投 げ て 。 "
    return head, body


def build_role_reply(role: Optional[str]) -> Tuple[str, str]:
    if role == "japache":
        return build_japache_role_reply()
    if role == "scout":
        return build_scout_role_reply()
    if role == "iindesuka":
        return build_iindesuka_role_reply()
    if role == "tanoshi":
        return build_tanoshi_role_reply()
    return build_yarude_role_reply()

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
    v = fetch_bot_state_value(conn, f"ctx:last_item:{chat_id}")
    if not str(v or "").strip():
        return False
    item_id = int(v)
    full_reason = f"{decision} {reason}".strip()
    upsert_decision_reason(conn, item_id, full_reason)
    score = 1 if decision == "採 用 " else 0 if decision == "保 留 " else -1 if decision == "見 送 り" else 0
    insert_decision_event(
        conn, item_id, decision, score, reason, decided_by="tg", source="tg"
    )
    tg_send(full_reason)
    return True


def resolve_item_from_text(conn: sqlite3.Connection, text: str) -> Optional[sqlite3.Row]:
    urls = URL_RE.findall(text or "")
    if urls:
        it = find_item_by_url(conn, urls[0])
        if it:
            return it
    hint = extract_title_hint(text)
    return find_item_by_title_hint(conn, hint)


def resolve_item(conn: sqlite3.Connection, text: str) -> Optional[sqlite3.Row]:
    return resolve_item_from_text(conn, text)


def fetch_item_row(conn: sqlite3.Connection, item_id: int):
    return conn.execute(
        "SELECT id,title,url FROM items WHERE id=? LIMIT 1",
        (item_id,),
    ).fetchone()


def get_item(conn, item_id):
    return fetch_item_row(conn, item_id)

def build_title_hint_for_context(text: str, q: str) -> str:
    return (
        extract_title_hint(text)
        or extract_title_hint(q)
        or (q.split()[0] if q else "")
    )


def resolve_item_from_context_key(conn: sqlite3.Connection, chat_id: str) -> Optional[sqlite3.Row]:
    v = fetch_bot_state_value(conn, f"ctx:last_item:{chat_id}")
    return get_item(conn, int(v)) if str(v or "").strip() else None


def resolve_item_from_title_hint(conn: sqlite3.Connection, text: str, q: str) -> Optional[sqlite3.Row]:
    hint = build_title_hint_for_context(text, q)
    return find_item_by_title_hint(conn, hint) if hint else None


def build_chat_query_context(text: str) -> str:
    return normalize_chat_query(text)


def resolve_item_initial(conn: sqlite3.Connection, text: str) -> Optional[sqlite3.Row]:
    return resolve_item(conn, text)


def resolve_item_fallback_chain(conn: sqlite3.Connection, chat_id: str, text: str, q: str) -> Optional[sqlite3.Row]:
    item = resolve_item_from_title_hint(conn, text, q)
    if item:
        return item
    return resolve_item_from_context_key(conn, chat_id)


def resolve_item_with_context(conn: sqlite3.Connection, chat_id: str, text: str):
    q = build_chat_query_context(text)
    item = resolve_item_initial(conn, text)
    if not item:
        item = resolve_item_fallback_chain(conn, chat_id, text, q)
    return item, q


def build_item_reply(
    conn: sqlite3.Connection,
    role: Optional[str],
    item: sqlite3.Row,
) -> str:
    head, body = build_role_reply(role)
    meta = get_item_meta(conn, int(item["id"]))
    return (
        f"{head}\n"
        f"{format_meta(meta)}\n"
        f"対  象  : {item['title']}\n"
        f"{item['url']}\n\n"
        f"{body}"
    )


def build_candidate_reply(role: Optional[str], q: str) -> str:
    head, body = build_role_reply(role)
    return f"{head}\n" f"対  象  候  補  : {q}\n\n" f"{body}"


def build_chat_reply(
    conn: sqlite3.Connection,
    role: Optional[str],
    item: Optional[sqlite3.Row],
    q: str,
) -> str:
    if item:
        return build_item_reply(conn, role, item)
    return build_candidate_reply(role, q)

def should_ignore_chat_text(text: str) -> bool:
    if not text:
        return True
    if text.startswith("/"):
        return True
    return False


def handle_chat_decision_if_any(
    conn: sqlite3.Connection,
    chat_id: str,
    text: str,
) -> bool:
    d = parse_decision(text)
    if not d:
        return False
    decision, reason = d
    return apply_chat_decision(conn, chat_id, decision, reason)


def handle_chat_item_followup(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    item: Optional[sqlite3.Row],
    role: Optional[str],
    text: str,
) -> None:
    if not item:
        return
    set_ctx_last_item(conn, row["chat_id"], int(item["id"]))
    enqueue_chat_job(
        conn, row["chat_id"], int(item["id"]), role or "", normalize_chat_query(text)
    )


def resolve_chat_role(text: str) -> Optional[str]:
    return role_from_text(text)


def build_chat_reply_for_item_context(
    conn: sqlite3.Connection,
    role: Optional[str],
    item: Optional[sqlite3.Row],
    q: str,
) -> str:
    return build_chat_reply(conn, role, item, q)


def resolve_chat_item_context(
    conn: sqlite3.Connection,
    chat_id: str,
    text: str,
):
    return resolve_item_with_context(conn, chat_id, text)


def normalize_handle_chat_text(row: sqlite3.Row) -> str:
    return (row["text"] or "").strip()


def get_handle_chat_cmd_id(row: sqlite3.Row) -> int:
    return row["id"]


def handle_chat(
    conn: sqlite3.Connection, row: sqlite3.Row
) -> Tuple[str, Optional[str]]:
    cmd_id = get_handle_chat_cmd_id(row)
    chat_id = str(row["chat_id"])
    text = normalize_handle_chat_text(row)

    if should_ignore_chat_text(text):
        return ("ignored", None)

    if handle_chat_decision_if_any(conn, chat_id, text):
        return ("chatted", None)

    role = resolve_chat_role(text)
    item, q = resolve_chat_item_context(conn, chat_id, text)
    reply = build_chat_reply_for_item_context(conn, role, item, q)

    tg_send(reply)
    handle_chat_item_followup(conn, row, item, role, text)
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
