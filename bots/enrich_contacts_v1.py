# -*- coding: utf-8 -*-
"""
enrich_contacts_v1.py v1.3

改善:
- official候補として platform/運営/ドキュメントサイトを採用しない（reddithelp, github*, docs.*など）
- Reddit投稿は本文テキストから外部URLを抽出（aタグ以外も拾う）
- メール抽出で HTMLエスケープ由来のゴミ（u003e 等）を除外
- 公式候補が取れない場合:
   - item_url がプラットフォームなら skip
   - それ以外は item_url を公式として fallback crawl
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import time
import urllib.parse
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import requests
import tldextract

ITEMS_TABLE = "items"
CONTACTS_TABLE = "contacts"
REVIEW_STATUS = "review"

ITEM_COL_ID = "id"
ITEM_COL_STATUS = "status"
ITEM_COL_URL = "url"

USER_AGENT = "OpenClawContactEnricher/1.3"
TIMEOUT = 20
SLEEP_SEC = 0.55

MAX_PAGES_DEFAULT = 18
MAX_DEPTH_DEFAULT = 3

# item_url がこのドメインなら「外部リンク」探しが基本
PLATFORM_DOMAINS = {"reddit.com", "github.com", "producthunt.com"}

# official候補としては採用しない（運営/ドキュメント/紹介/SNS/マーケット）
BLOCK_DOMAINS = {
    # markets
    "amazon.co.jp", "amazon.com", "rakuten.co.jp", "yahoo.co.jp", "mercari.com",
    "aliexpress.com", "temu.com", "shein.com",
    # sns
    "facebook.com", "instagram.com", "x.com", "twitter.com", "tiktok.com", "youtube.com",
    "linkedin.com",
    # platform ops/docs
    "redditinc.com", "reddithelp.com", "support.reddithelp.com",
    "github.com", "githubstatus.com", "github.community", "docs.github.com",
    # misc
    "google.com", "line.me",
    "claude.ai",
}

# これらのドメインは「公式候補」として弱いので減点/除外
BAD_DOMAIN_SUBSTR = (
    "support.", "help.", "docs.", "status.", "community.", "policy.", "policies."
)

# URLパスで除外（規約/ポリシー/ステータス/求人/紹介 etc）
BAD_PATH_HINTS = (
    "/policies", "/policy", "/privacy", "/terms", "/legal", "/status",
    "/careers", "/jobs", "/press",
    "/referral", "/signup", "/login",
)

OFFICIAL_HINTS = (
    "official", "公式", "website", "homepage", "site",
    "company", "brand", "about", "contact",
    "お問い合わせ", "運営", "公式サイト", "webサイト",
)

PRIORITY_PATH_HINTS = ("/contact", "/support", "/help", "/about", "/company", "/impressum")

EMAIL_RE = re.compile(r"(?i)\b([a-z0-9._%+\-]+)@([a-z0-9.\-]+\.[a-z]{2,})\b")
URL_RE = re.compile(r"(?i)\bhttps?://[^\s<>\")]+")  # 本文からURL抽出用


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def registrable_domain(url: str) -> Optional[str]:
    try:
        host = urllib.parse.urlparse(url).hostname
        if not host:
            return None
        ext = tldextract.extract(host)
        if not ext.domain or not ext.suffix:
            return None
        return f"{ext.domain}.{ext.suffix}".lower()
    except Exception:
        return None


def is_platform(url: str) -> bool:
    d = registrable_domain(url)
    return d in PLATFORM_DOMAINS if d else False


def in_block_domain(url: str) -> bool:
    d = registrable_domain(url)
    return d in BLOCK_DOMAINS if d else False


def looks_bad_domain(url: str) -> bool:
    host = urllib.parse.urlparse(url).hostname or ""
    host = host.lower()
    return any(s in host for s in BAD_DOMAIN_SUBSTR)


def looks_bad_path(url: str) -> bool:
    u = url.lower()
    return any(p in u for p in BAD_PATH_HINTS)


def priority_score(url: str) -> int:
    u = url.lower()
    return sum(4 for p in PRIORITY_PATH_HINTS if p in u)


def email_domain(email: str) -> str:
    return email.split("@", 1)[1].lower().strip()


def clean_email(e: str) -> Optional[str]:
    """
    htmlエスケープ由来のゴミを除外。
    例: u003eprivacy@github.com → privacy@github.com にしたい気持ちもあるが、
        ここでは安全に「u003e含むなら捨てる」。
    """
    e = (e or "").strip().lower()
    if not e or "@" not in e:
        return None
    if "u003e" in e or "\\u003e" in e or "&gt;" in e:
        return None
    if len(e) < 6 or len(e) > 254:
        return None
    return e


def extract_emails(html: str) -> Set[str]:
    found = set()

    for m in EMAIL_RE.finditer(html or ""):
        e = clean_email(f"{m.group(1)}@{m.group(2)}")
        if e:
            found.add(e)

    for m in re.finditer(r'(?i)href\s*=\s*["\']mailto:([^"\']+)["\']', html or ""):
        raw = m.group(1)
        addr = raw.split("?", 1)[0].strip()
        for part in re.split(r"[;,]", addr):
            part = clean_email(part)
            if part:
                found.add(part)

    return found


def extract_a_links(html: str, base_url: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    if not html:
        return out
    for m in re.finditer(r'(?is)<a[^>]+href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', html):
        href = (m.group(1) or "").strip()
        inner = re.sub(r"(?is)<.*?>", " ", (m.group(2) or ""))
        inner = re.sub(r"\s+", " ", inner).strip()
        if not href or href.startswith("#"):
            continue
        if href.lower().startswith(("mailto:", "javascript:")):
            continue
        abs_url = urllib.parse.urljoin(base_url, href).split("#", 1)[0]
        out.append((abs_url, inner))
    return out


def extract_text_urls(html: str) -> Set[str]:
    """
    aタグ以外（本文）からURLを拾う（Reddit対策）
    """
    urls = set()
    for m in URL_RE.finditer(html or ""):
        u = m.group(0).strip().rstrip(").,]}")
        if u:
            urls.add(u)
    return urls


def fetch(session: requests.Session, url: str) -> Optional[str]:
    try:
        r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code >= 400:
            return None
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" not in ctype and "application/xhtml+xml" not in ctype:
            return None
        r.encoding = r.apparent_encoding or r.encoding
        return r.text
    except Exception:
        return None


def pick_official_candidate(item_html: str, item_url: str) -> Optional[str]:
    """
    v1.3: 公式候補を抽出
    優先順:
      1) aタグ外部リンク（block除外/悪いドメイン除外/悪いパス除外）
      2) 本文から拾ったURL（同上）
    """
    item_dom = registrable_domain(item_url) or ""
    scored: List[Tuple[int, str]] = []

    def consider(url: str, hint: str, base_score: int):
        nurl = normalize_url(url)
        if not nurl:
            return
        if in_block_domain(nurl):
            return
        if looks_bad_domain(nurl):
            return
        if looks_bad_path(nurl):
            return

        cand_dom = registrable_domain(nurl) or ""
        if not cand_dom:
            return
        # itemと同一ドメイン（reddit/github/producthunt内リンク）は除外
        if cand_dom == item_dom:
            return

        score = base_score
        hint_l = (hint or "").lower()

        for k in OFFICIAL_HINTS:
            if k.lower() in hint_l:
                score += 8

        score += priority_score(nurl)

        # トップに近いと少し加点
        if re.search(r"//[^/]+/?$", nurl):
            score += 3

        # トラッカー減点
        if any(x in nurl.lower() for x in ("utm_", "affiliate", "track", "click", "redir", "redirect", "ref=")):
            score -= 2

        scored.append((score, nurl))

    # 1) aタグ
    for url, hint in extract_a_links(item_html, item_url):
        consider(url, hint, base_score=20)

    # 2) 本文URL（Reddit等）
    for u in extract_text_urls(item_html):
        consider(u, "text_url", base_score=12)

    if not scored:
        return None

    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[0][1]


@dataclass(frozen=True)
class FoundEmail:
    email: str
    found_url: str


def crawl_same_domain_for_emails(start_url: str, max_pages: int, max_depth: int) -> List[FoundEmail]:
    start_url = normalize_url(start_url)
    base = registrable_domain(start_url)
    if not base:
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 優先リンク先に寄せるため priority付きキュー
    q: List[Tuple[str, int, int]] = [(start_url, 0, 0)]
    seen: Set[str] = set()
    found: Dict[str, FoundEmail] = {}

    def push(url: str, depth: int):
        pri = -priority_score(url)  # priorityが高いほど先
        q.append((url, depth, pri))

    while q and len(seen) < max_pages:
        q.sort(key=lambda x: x[2])  # priが小さいほど先（負値が強い）
        url, depth, _pri = q.pop(0)

        if url in seen:
            continue
        seen.add(url)

        # 同一registrable_domainのみ
        if registrable_domain(url) != base:
            continue

        html = fetch(session, url)
        time.sleep(SLEEP_SEC)
        if not html:
            continue

        for e in extract_emails(html):
            dom = email_domain(e)
            if dom == base or dom.endswith("." + base):
                found.setdefault(e, FoundEmail(email=e, found_url=url))

        if depth >= max_depth:
            continue

        for link, _hint in extract_a_links(html, url):
            link = normalize_url(link)
            if not link or link in seen:
                continue
            if registrable_domain(link) != base:
                continue
            push(link, depth + 1)

    return list(found.values())


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_review_items(conn: sqlite3.Connection, limit: int) -> List[sqlite3.Row]:
    sql = f"""
      SELECT {ITEM_COL_ID} as id, {ITEM_COL_URL} as url
      FROM {ITEMS_TABLE}
      WHERE {ITEM_COL_STATUS} = ?
      ORDER BY {ITEM_COL_ID} ASC
      LIMIT ?
    """
    return list(conn.execute(sql, (REVIEW_STATUS, limit)))


def insert_contact_ignore(conn: sqlite3.Connection, item_url: str, email: str, domain: str, source: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO contacts (item_url,email,domain,source) VALUES (?,?,?,?)",
        (item_url, email, domain, source),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("OCLAW_DB", "data/openclaw.db"))
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT)
    ap.add_argument("--max-depth", type=int, default=MAX_DEPTH_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = connect_db(args.db)
    items = fetch_review_items(conn, args.limit)
    if not items:
        print("No review items.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for row in items:
        item_url = normalize_url(row["url"])
        print(f"\nitem_url={item_url}")

        html = fetch(session, item_url)
        time.sleep(SLEEP_SEC)

        official: Optional[str] = None
        if html:
            official = pick_official_candidate(html, item_url)

        if not official:
            if is_platform(item_url) or in_block_domain(item_url):
                print("  official_candidate=NONE (platform/blocked) -> skip")
                continue
            official = item_url
            source = "fallback_item_url"
            print("  official_candidate=NONE -> fallback to item_url as official")
        else:
            source = "official_from_item_links"
            print(f"  official_candidate={official}")

        emails = crawl_same_domain_for_emails(official, args.max_pages, args.max_depth)
        if not emails:
            print("  no emails found")
            continue

        for fe in emails:
            dom = email_domain(fe.email)
            if args.dry_run:
                print(f"  [dry] {fe.email} dom={dom} found_at={fe.found_url}")
            else:
                insert_contact_ignore(conn, item_url, fe.email, dom, source)

        if not args.dry_run:
            conn.commit()

    if args.dry_run:
        print("\nDone (dry-run).")
    else:
        print("\nDone.")

if __name__ == "__main__":
    main()
