# -*- coding: utf-8 -*-
"""
role_training_v1.py v1.1
- fetch失敗時にstatus_code/例外を表示
- Cloudflare/403が出やすいサイトは代替フィードを追加（安定運用優先）
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

UA = "OpenClawRoleTrainer/1.1"
TIMEOUT = 25
SLEEP = 0.6

ROLE_FEEDS: Dict[str, List[Tuple[str, str]]] = {
    "yarde": [
        ("HN Frontpage", "https://hnrss.org/frontpage"),
        ("GitHub Blog", "https://github.blog/feed/"),
    ],
    "scout": [
        ("Product Hunt", "https://www.producthunt.com/feed"),
        ("HN Show", "https://hnrss.org/show"),
    ],
    "japache": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ],
    # 収益/価格/モデルの学習は安定ソースへ寄せる
    "iindesuka": [
        ("Y Combinator Library", "https://www.ycombinator.com/library/feed"),
        ("Lenny's Newsletter", "https://www.lennysnewsletter.com/feed"),
        ("SaaStr", "https://www.saastr.com/feed/"),
        ("Stripe Blog (try)", "https://stripe.com/blog/rss"),
        ("a16z (try)", "https://a16z.com/feed/"),
    ],
    # 営業/アウトリーチ
    "tanoshi": [
        ("HubSpot Sales", "https://blog.hubspot.com/sales/rss.xml"),
        ("Close.com Blog", "https://close.com/blog/rss/"),
        ("Gong Blog (try)", "https://www.gong.io/blog/feed/"),
    ],
}

TOPIC_RULES = [
    ("mcp", re.compile(r"\bmcp\b|model\s*context\s*protocol", re.I)),
    ("agent", re.compile(r"\bagent\b|orchestrator|workflow", re.I)),
    ("pricing", re.compile(r"\bpricing\b|price|subscription|saas", re.I)),
    ("import", re.compile(r"\bimport\b|distributor|wholesale|retail", re.I)),
    ("sales", re.compile(r"\bsales\b|outreach|cold email|prospecting", re.I)),
    ("product", re.compile(r"\bproduct\b|launch|release", re.I)),
]

def guess_topic(title: str, link: str) -> str:
    s = f"{title} {link}"
    for topic, pat in TOPIC_RULES:
        if pat.search(s):
            return topic
    return "general"

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"(?is)<.*?>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

@dataclass
class FeedItem:
    title: str
    link: str
    summary: str

def fetch_text(url: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    try:
        r = requests.get(
            url,
            timeout=TIMEOUT,
            headers={
                "User-Agent": UA,
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )
        status = r.status_code
        if status >= 400:
            return None, status, f"http_{status}"
        r.encoding = r.apparent_encoding or r.encoding
        return r.text, status, None
    except Exception as e:
        return None, None, f"exc:{type(e).__name__}:{e}"

def parse_rss(xml_text: str, limit: int) -> List[FeedItem]:
    out: List[FeedItem] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return out

    # Atom
    if root.tag.lower().endswith("feed"):
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for e in entries[:limit]:
            title = (e.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link_el = e.find("{http://www.w3.org/2005/Atom}link")
            link = (link_el.get("href") if link_el is not None else "") or ""
            summ = (e.findtext("{http://www.w3.org/2005/Atom}summary") or e.findtext("{http://www.w3.org/2005/Atom}content") or "")
            out.append(FeedItem(clean_text(title), link.strip(), clean_text(summ)[:500]))
        return out

    # RSS
    items = root.findall(".//item")
    for it in items[:limit]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        summ = (it.findtext("description") or it.findtext("content:encoded") or "")
        out.append(FeedItem(clean_text(title), link, clean_text(summ)[:500]))
    return out

def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def insert_brief(conn: sqlite3.Connection, role: str, topic: str, source_url: str, title: str, summary: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO role_briefs(role, topic, source_url, title, summary)
        VALUES(?,?,?,?,?)
        """,
        (role, topic, source_url, title, summary),
    )
    return cur.rowcount == 1

def run_for_role(db_path: str, role: str, limit: int) -> int:
    feeds = ROLE_FEEDS.get(role, [])
    if not feeds:
        print(f"[{role}] no feeds configured")
        return 0

    conn = connect_db(db_path)
    added = 0

    print(f"\n=== role={role} ===")
    for label, feed_url in feeds:
        print(f"- fetch {label}: {feed_url}")
        xml_text, status, err = fetch_text(feed_url)
        time.sleep(SLEEP)
        if not xml_text:
            extra = []
            if status is not None:
                extra.append(f"status={status}")
            if err:
                extra.append(err)
            print("  (skip) fetch failed" + (f" ({', '.join(extra)})" if extra else ""))
            continue

        items = parse_rss(xml_text, limit=limit)
        if not items:
            print("  (skip) parse empty")
            continue

        for it in items:
            if not it.link:
                continue
            topic = guess_topic(it.title, it.link)
            ok = insert_brief(conn, role, topic, it.link, it.title, it.summary)
            if ok:
                added += 1

    conn.commit()
    conn.close()
    print(f"[{role}] added={added}")
    return added

def main():
    import os
    feeds_file=os.environ.get("FEEDS_FILE")
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/openclaw.db")
    ap.add_argument("--role", default="all")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    roles = list(ROLE_FEEDS.keys()) if args.role == "all" else [args.role]
    total = 0
    for r in roles:
        total += run_for_role(args.db, r, args.limit)

    print(f"\nDone. total_added={total}")

if __name__ == "__main__":
    main()
