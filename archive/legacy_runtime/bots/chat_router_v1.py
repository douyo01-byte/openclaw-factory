from __future__ import annotations

import argparse
import os
import re
import sqlite3



def _oc_health_text(conn):
    q = conn.execute("""
    select
      sum(case when status='approved' and coalesce(project_decision,'')='execute_now' and coalesce(guard_status,'')='safe' then 1 else 0 end),
      sum(case when status='approved' and (coalesce(project_decision,'')='backlog' or (coalesce(guard_status,'')!='' and coalesce(guard_status,'')!='safe')) then 1 else 0 end),
      sum(case when status='open' or coalesce(pr_status,'')='open' or coalesce(dev_stage,'')='open' then 1 else 0 end),
      sum(case when status='merged' then 1 else 0 end)
    from dev_proposals
    """).fetchone()
    p = conn.execute("""
    select count(*)
    from ceo_hub_events
    where event_type='learning_pattern'
    """).fetchone()[0]
    return f"OpenClaw Company Health\nmainstream={q[0] or 0}\nbacklog={q[1] or 0}\nopen_pr={q[2] or 0}\nmerged={q[3] or 0}\nlearning_pattern={p or 0}"

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


def handle_chat(
    conn: sqlite3.Connection, row: sqlite3.Row
) -> Tuple[str, Optional[str]]:
    cmd_id = row["id"]
    chat_id = str(row["chat_id"])
    text = (row["text"] or "").strip()

    if not text:
        return ("ignored", None)

    if text.strip() in ("/company", "/status"):
        return _oc_health_text(conn)
    if text.startswith("/"):
        return ("ignored", None)
    d = parse_decision(text)
    if d:
        decision, reason = d
        r = conn.execute(
            "SELECT v FROM bot_state WHERE k=? LIMIT 1", (f"ctx:last_item:{chat_id}",)
        ).fetchone()
        if r and str(r["v"]).strip():
            upsert_decision_reason(conn, int(r["v"]), f"{decision} {reason}".strip())
            score = (
                1
                if decision == "採用"
                else 0 if decision == "保留" else -1 if decision == "見送り" else 0
            )
            insert_decision_event(
                conn, int(r["v"]), decision, score, reason, decided_by="tg", source="tg"
            )
            tg_send(f"{decision} {reason}".strip())
            return ("chatted", None)

    role = role_from_text(text)
    item = resolve_item(conn, text)
    if not item:
        q = strip_role_words(text)
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
    head, body = build_role_reply(role)

    if item:
        try:
            conn.execute(
                "INSERT INTO chat_jobs(chat_id, item_id, role, query, status, created_at, updated_at) VALUES(?,?,?,?, 'new', datetime('now'), datetime('now'))",
                (
                    chat_id,
                    int(item["id"]),
                    role or "",
                    text,
                ),
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
        reply = f"{head}\n" f"対象候補: {q}\n\n" f"{body}"

    tg_send(reply)
    if item:
        enqueue_chat_job(
            conn, row["chat_id"], int(item["id"]), role or "", strip_role_words(text)
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
