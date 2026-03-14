import os
import re
import json
import time
import sqlite3


def _load_persona_from_env():
    core = os.environ.get("CORE_PERSONA_FILE")
    role = os.environ.get("PERSONA_FILE")
    t = []
    if core and os.path.exists(core):
        t.append(open(core, "r", encoding="utf-8").read().strip())
    if role and os.path.exists(role):
        t.append(open(role, "r", encoding="utf-8").read().strip())
    return "\n\n".join([x for x in t if x])


PERSONA = _load_persona_from_env()

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

from oclibs.telegram import send as tg_send

load_dotenv()
client = OpenAI()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

HEADERS = {"User-Agent": "openclaw-factory/0.1 (+contact: douyo01-byte)"}
DB_PATH = '/Users/doyopc/AI/openclaw-factory/data/openclaw.db'

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass
class Item:
    source: str
    title: str
    url: str
    summary: str = ""
    japan_presence: str = "unknown"  # likely/unlikely/unknown
    score: int = 0
    rationale_jp: str = ""
    category_guess: str = ""
    emails: List[str] = None
    contact_urls: List[str] = None

    def __post_init__(self):
        self.emails = self.emails or []
        self.contact_urls = self.contact_urls or []


def db() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def is_seen(url: str) -> bool:
    con = db()
    cur = con.cursor()
    cur.execute("SELECT 1 FROM items WHERE url=? LIMIT 1", (url,))
    row = cur.fetchone()
    con.close()
    return row is not None


def upsert_item(it: Item) -> None:
    con = db()
    cur = con.cursor()
    cur.execute(
        """
      INSERT INTO items(url, title, source)
      VALUES(?,?,?)
      ON CONFLICT(url) DO UPDATE SET
        last_seen_at = datetime('now'),
        title=excluded.title,
        source=excluded.source
    """,
        (it.url, it.title, it.source),
    )
    con.commit()
    con.close()


def load_sources(path="configs/sources.json") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["sources"]


def fetch_html(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code >= 400:
            return None
        return r.text
    except Exception:
        return None


def parse_list(selector_mode: str, base_url: str, html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "xml")
    out: List[Dict[str, str]] = []

    def add(title: str, href: str, summary: str = ""):
        if not title or not href:
            return
        url = href if href.startswith("http") else urljoin(base_url, href)
        title = re.sub(r"\s+", " ", title).strip()
        summary = re.sub(r"\s+", " ", summary).strip()
        out.append({"title": title, "url": url, "summary": summary[:400]})

    # --- Kicktraq ---
    if selector_mode == "kicktraq":
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            txt = a.get_text(" ", strip=True)
            # projects/xxxx/xxxx/ の形を拾う
            if "/projects/" in href and txt and len(txt) > 6:
                add(txt, href)
        return dedupe(out)

    # --- Product Hunt ---
    if selector_mode == "producthunt":
        # ざっくり “post” のリンクっぽいのを拾う
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.startswith("/posts/"):
                title = a.get_text(" ", strip=True)
                if title:
                    add(title, href)
        return dedupe(out)

    # --- HN Show ---
    if selector_mode == "hn_show":
        for a in soup.select("a.storylink, span.titleline > a"):
            href = a.get("href", "")
            title = a.get_text(" ", strip=True)
            add(title, href)
        return dedupe(out)

    # --- BetaList ---
    if selector_mode == "betalist":
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "/startup/" in href:
                title = a.get_text(" ", strip=True)
                add(title, href)
        return dedupe(out)

    # --- JP crowdfund（各サイトは後で精度改善。まずはリンク拾い） ---
    if selector_mode.startswith("jp_"):
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            title = a.get_text(" ", strip=True)
            # 短すぎるのは除外
            if title and len(title) >= 8:
                add(title, href)
        return dedupe(out)

    return dedupe(out)


def dedupe(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for x in items:
        u = x["url"]
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(x)
    return out


def extract_contacts(url: str) -> Dict[str, List[str]]:
    html = fetch_html(url)
    if not html:
        return {"emails": [], "contact_urls": []}

    soup = BeautifulSoup(html, "xml")
    text = soup.get_text(" ", strip=True)
    emails = sorted(set(EMAIL_RE.findall(text)))[:10]

    contact_urls = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue
        h = href.lower()
        if any(
            k in h for k in ["contact", "support", "help", "inquiry", "about", "press"]
        ):
            contact_urls.append(href if href.startswith("http") else urljoin(url, href))
    contact_urls = sorted(set(contact_urls))[:10]

    return {"emails": emails, "contact_urls": contact_urls}


def llm_assess(it: Item) -> Dict[str, Any]:
    prompt = f"""
あなたは「海外（クラファン＋スタートアップ）→日本未上陸→独占販売候補」を選別する審査官です。
カテゴリは限定しないが、ガジェット/家電は優先評価。
“規約に触れにくい発掘”が前提なので、危険/違法/薬機法系は低評価。

出力はJSONのみ：
{{
  "japan_presence": "likely|unlikely|unknown",
  "score": 0-100,
  "category_guess": "短く",
  "rationale_jp": "日本語で短く（注意点も）"
}}

案件:
タイトル: {it.title}
URL: {it.url}
概要: {it.summary}
"""
    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    txt = res.choices[0].message.content.strip()
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        return {
            "japan_presence": "unknown",
            "score": 0,
            "category_guess": "不明",
            "rationale_jp": "JSON取得失敗",
        }
    try:
        return json.loads(m.group(0))
    except Exception:
        return {
            "japan_presence": "unknown",
            "score": 0,
            "category_guess": "不明",
            "rationale_jp": "JSONパース失敗",
        }


def format_meeting(top: List[Item], jp_trends: List[Item]) -> str:
    lines = []
    lines.append(
        "ヤルデ（総括）🧠 会議：海外発掘→日本未上陸推定→連絡先抽出（営業文は未作成）"
    )
    lines.append("")
    lines.append(
        "スカウン：風まかせに拾う。カテゴリは縛らないが、ガジェット/家電は強めに見る。"
    )
    lines.append("")
    lines.append("==== 海外候補 TOP ====")
    for i, it in enumerate(top, 1):
        lines.append(
            f"【候補{i}】Score={it.score} / 日本未上陸={it.japan_presence} / 種別={it.category_guess}"
        )
        lines.append(it.title)
        lines.append(it.url)
        if it.summary:
            lines.append(
                f"概要: {it.summary[:160]}{'…' if len(it.summary)>160 else ''}"
            )
        lines.append(f"判断: {it.rationale_jp}")
        if it.emails:
            lines.append("メール: " + ", ".join(it.emails))
        if it.contact_urls:
            lines.append("問い合わせ候補: " + ", ".join(it.contact_urls[:3]))
        lines.append("—")

    lines.append("")
    lines.append("==== 日本クラファン（売れてる/目立つ雰囲気） ====")
    for it in jp_trends[:5]:
        lines.append(f"- {it.title} ({it.source})")
        lines.append(f"  {it.url}")

    lines.append("")
    lines.append(
        "次アクション：上位候補の公式サイトContact精査→法人情報→独占交渉可否を判断。"
    )
    return "\n".join(lines)


def main():
    sources = load_sources()
    overseas: List[Item] = []
    jp: List[Item] = []

    for s in sources:
        html = fetch_html(s["url"])
        if not html:
            continue
        items = parse_list(s.get("selector_mode", ""), s["url"], html)
        for x in items[:40]:
            it = Item(
                source=s["name"],
                title=x["title"],
                url=x["url"],
                summary=x.get("summary", ""),
            )
            # 既出スキップ（永続）
            if is_seen(it.url):
                continue
            upsert_item(it)

            if s.get("selector_mode", "").startswith("jp_"):
                jp.append(it)
            else:
                overseas.append(it)
        time.sleep(0.6)

    if not overseas:
        _m = "ヤルデ：新規の海外候補が拾えませんでした（既出スキップが効いてる/ソースが弱い可能性）。"
        if not _tg_msg_sent(_m):
            tg_send(_m)
            return

    # コスト制御：評価は最大20件
    batch = overseas[:20]
    for it in batch:
        time.sleep(0.9)
        j = llm_assess(it)
        it.japan_presence = j.get("japan_presence", "unknown")
        it.score = int(j.get("score", 0))
        it.category_guess = j.get("category_guess", "")
        it.rationale_jp = j.get("rationale_jp", "")

    ranked = sorted(batch, key=lambda x: x.score, reverse=True)[:5]

    # 連絡先抽出は上位のみ（負荷抑制）
    for it in ranked:
        time.sleep(1.0)
        c = extract_contacts(it.url)
        it.emails = c["emails"]
        it.contact_urls = c["contact_urls"]

    top3 = ranked[:3]
    msg = format_meeting(top3, jp)

    if not _tg_url_sent(top3[0].url):
        tg_send(msg)


if __name__ == "__main__":
    main()
