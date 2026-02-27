from __future__ import annotations

import argparse
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from urllib.parse import urljoin, urlparse

import requests

from oclibs.telegram import send as tg_send

DB_DEFAULT = os.environ.get("OCLAW_DB_PATH", "./data/openclaw.db")

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
JP_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
CONTACT_HINT_RE = re.compile(r"(contact|support|help|inquiry|お問い合わせ|問合せ|問い合わせ)", re.IGNORECASE)
AMAZON_RAKUTEN_RE = re.compile(r"(amazon\.co\.jp|rakuten\.co\.jp|楽天|アマゾン)", re.IGNORECASE)

PATH_CANDIDATES = ["/", "/contact", "/about", "/privacy", "/terms", "/company"]

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fetch(url: str, timeout: int = 15) -> Tuple[int, str]:
    headers = {"User-Agent": "OpenClawResearch/1.0"}
    r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    return r.status_code, r.text or ""

def normalize_base(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    p = urlparse(u)
    if not p.scheme:
        u = "https://" + u
    return u

def extract_signals(html: str) -> Dict[str, Any]:
    emails = sorted(set(EMAIL_RE.findall(html or "")))
    has_jp = bool(JP_RE.search(html or ""))
    has_contact_hint = bool(CONTACT_HINT_RE.search(html or ""))
    has_amazon_rakuten = bool(AMAZON_RAKUTEN_RE.search(html or ""))
    return {
        "emails": emails[:10],
        "has_jp": has_jp,
        "has_contact_hint": has_contact_hint,
        "has_amazon_rakuten": has_amazon_rakuten,
    }

def summarize(signals_by_path: List[Tuple[str, int, Dict[str, Any]]]) -> Dict[str, Any]:
    emails = []
    jp = False
    contact = False
    amzrk = False
    ok_paths = []
    for path, code, sig in signals_by_path:
        if code and 200 <= code < 400:
            ok_paths.append(path)
        for e in sig.get("emails", []):
            if e not in emails:
                emails.append(e)
        jp = jp or bool(sig.get("has_jp"))
        contact = contact or bool(sig.get("has_contact_hint"))
        amzrk = amzrk or bool(sig.get("has_amazon_rakuten"))
    return {
        "emails": emails[:10],
        "has_jp": jp,
        "has_contact_hint": contact,
        "has_amazon_rakuten": amzrk,
        "ok_paths": ok_paths,
    }

def get_item(conn: sqlite3.Connection, item_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT id, title, url FROM items WHERE id=? LIMIT 1", (item_id,)).fetchone()

def set_ctx_last_item(conn: sqlite3.Connection, chat_id: str, item_id: int) -> None:
    conn.execute(
        "INSERT INTO bot_state(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (f"ctx:last_item:{chat_id}", str(item_id)),
    )

def enqueue_contact(conn: sqlite3.Connection, item_id: int, email: str, source: str) -> None:
    try:
        conn.execute(
            "INSERT INTO contacts(item_id, email, source, created_at) VALUES(?,?,?,datetime('now'))",
            (item_id, email, source),
        )
    except Exception:
        pass

def upsert_role_brief(conn: sqlite3.Connection, role: str, title: str, url: str, text: str) -> None:
    cols = {c["name"] for c in conn.execute("PRAGMA table_info(role_briefs);").fetchall()}
    fields = []
    values = []
    if "role" in cols:
        fields.append("role"); values.append(role)
    if "topic" in cols:
        fields.append("topic"); values.append((title or "unknown"))
    if "source_url" in cols:
        fields.append("source_url"); values.append((url or "about:blank"))
    if "title" in cols:
        fields.append("title"); values.append(title)
    if "url" in cols:
        fields.append("url"); values.append(url)
    if "text" in cols:
        fields.append("text"); values.append(text)
    if "score" in cols:
        fields.append("score"); values.append(0)
    if "created_at" in cols:
        fields.append("created_at"); values.append(now_str())
    if not fields:
        return
    q = "INSERT INTO role_briefs(" + ",".join(fields) + ") VALUES(" + ",".join(["?"] * len(fields)) + ")"
    conn.execute(q, tuple(values))

def build_reply(role: Optional[str], item_title: str, item_url: str, summary: Dict[str, Any]) -> str:
    head = "🧠 ヤルデ"
    if role == "japache":
        head = "🕵️ ジャパチェ"
    elif role == "scout":
        head = "🌍 スカウン"
    elif role == "iindesuka":
        head = "💰 イインデスカ"
    elif role == "tanoshi":
        head = "🔥 タノシ"

    emails = summary.get("emails") or []
    ok_paths = summary.get("ok_paths") or []
    has_jp = summary.get("has_jp")
    has_contact = summary.get("has_contact_hint")
    has_amzrk = summary.get("has_amazon_rakuten")

    lines = []
    lines.append(f"{head}")
    lines.append(f"対象: {item_title}")
    lines.append(f"{item_url}")
    lines.append("")
    lines.append("調査結果")
    lines.append(f"取得できたページ: {', '.join(ok_paths) if ok_paths else 'なし'}")
    lines.append(f"日本語兆候: {'あり' if has_jp else 'なし'}")
    lines.append(f"問い合わせ導線ヒント: {'あり' if has_contact else 'なし'}")
    lines.append(f"Amazon/楽天兆候: {'あり' if has_amzrk else 'なし'}")
    lines.append(f"メール候補: {', '.join(emails) if emails else '未検出'}")
    lines.append("")
    lines.append("次どうする？")
    lines.append("採用/保留/見送り のどれかで返して。理由も一言あると decision_reason に残せるようにする。")
    return "\n".join(lines)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    conn = connect_db(args.db)

    jobs = conn.execute(
        "SELECT id, chat_id, item_id, role, query FROM chat_jobs WHERE status='new' LIMIT ?",
        (args.limit,),
    ).fetchall()

    processed = 0
    for job in jobs:
        job_id = int(job["id"])
        chat_id = str(job["chat_id"])
        item_id = job["item_id"]
        role = (job["role"] or "").strip() or "jpcheck"

        if not item_id:
            conn.execute("UPDATE chat_jobs SET status='error', updated_at=datetime('now'), error=? WHERE id=?",
                         ("missing item_id", job_id))
            continue

        item = get_item(conn, int(item_id))
        if not item:
            conn.execute("UPDATE chat_jobs SET status='error', updated_at=datetime('now'), error=? WHERE id=?",
                         ("item not found", job_id))
            continue

        base = normalize_base(item["url"])
        if not base:
            conn.execute("UPDATE chat_jobs SET status='error', updated_at=datetime('now'), error=? WHERE id=?",
                         ("missing url", job_id))
            continue

        signals_by_path = []
        for path in PATH_CANDIDATES:
            try:
                u = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
                code, html = fetch(u)
                sig = extract_signals(html)
                signals_by_path.append((path, code, sig))
            except Exception:
                signals_by_path.append((path, 0, {"emails": [], "has_jp": False, "has_contact_hint": False, "has_amazon_rakuten": False}))

        summary = summarize(signals_by_path)

        for e in summary.get("emails") or []:
            enqueue_contact(conn, int(item["id"]), e, "chat_research")

        reply = build_reply(role, item["title"], item["url"], summary)

        upsert_role_brief(conn, role or "yarde", item["title"], item["url"], reply)
        if item.get("id") is not None:
            set_ctx_last_item(conn, chat_id, int(item["id"]))

        tg_send(reply)

        conn.execute("UPDATE chat_jobs SET status='done', updated_at=datetime('now'), error=NULL WHERE id=?", (job_id,))
        processed += 1
        conn.commit()
        time.sleep(0.2)

    conn.close()
    print(f"Done. processed={processed}")

if __name__ == "__main__":
    main()
