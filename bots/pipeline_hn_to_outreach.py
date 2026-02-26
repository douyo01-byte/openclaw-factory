import os, json, re, time
from dataclasses import dataclass
from typing import List
from urllib.parse import quote_plus, urlparse

import feedparser
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright

load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
client = OpenAI()

@dataclass
class Candidate:
    title: str
    url: str
    summary: str
    japan_presence: str = "unknown"
    score: int = 0
    rationale: str = ""
    email_en: str = ""

def fetch_hn(n=10) -> List[Candidate]:
    feed = feedparser.parse("https://hnrss.org/frontpage")
    items = feed.entries[:n]
    out = []
    for it in items:
        out.append(Candidate(
            title=(it.get("title","") or "")[:200],
            url=it.get("link",""),
            summary=re.sub(r"\s+"," ", it.get("summary","") or "")[:400]
        ))
    return out

def ddg_collect_domains(query: str) -> list[str]:
    """DuckDuckGo検索結果からリンク先ドメインを最大10件集める（タイトルは見ない）"""
    url = f"https://duckduckgo.com/?q={quote_plus(query)}"
    domains = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(20000)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)

            # 結果リンクを拾う（Aタグのhref）
            # 仕様変更に強くするため、hrefからドメイン抽出
            links = page.query_selector_all("a[href]")
            for a in links:
                href = a.get_attribute("href") or ""
                if href.startswith("http"):
                    host = urlparse(href).netloc.lower()
                    if host and "duckduckgo.com" not in host:
                        domains.append(host)
                if len(domains) >= 10:
                    break

            browser.close()
    except Exception:
        pass

    # 重複排除しつつ返す
    uniq = []
    seen = set()
    for d in domains:
        if d in seen:
            continue
        seen.add(d)
        uniq.append(d)
    return uniq

def japan_presence_check(title: str) -> str:
    """
    日本存在チェック（軽量・低頻度）：
    - DDG検索結果に .jp ドメインが出たら likely
    - 出なければ unlikely
    """
    q = f"{title} 代理店 日本語"
    domains = ddg_collect_domains(q)

    if any(d.endswith(".jp") for d in domains):
        return "likely"
    return "unlikely"

def landing_title(url: str) -> str:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(20000)
            page.goto(url, wait_until="domcontentloaded")
            t = (page.title() or "")[:200]
            browser.close()
            return t
    except Exception as e:
        return f"(landing title failed: {type(e).__name__})"

def llm_score_and_email(c: Candidate) -> dict:
    prompt = f"""
You are evaluating startups/products for Japan-exclusive distribution opportunities.
Return ONLY JSON:
{{
  "score": <0-100 integer>,
  "rationale_jp": "<2-4 lines Japanese rationale>",
  "email_en": "<short English outreach email proposing Japan-exclusive distributor discussion>"
}}
Startup/Product:
title: {c.title}
url: {c.url}
summary: {c.summary}
japan_presence: {c.japan_presence}
landing_title: {landing_title(c.url)}
"""
    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":"Return only JSON. No markdown."},
            {"role":"user","content":prompt}
        ],
        response_format={"type":"json_object"},
    )
    return json.loads(res.choices[0].message.content or "{}")

def main():
    cands = fetch_hn(10)
    print("Fetched:", len(cands))

    # 日本存在チェック（礼儀として間隔を空ける）
    for c in cands:
        time.sleep(1.0)
        c.japan_presence = japan_presence_check(c.title)

    # 日本未上陸っぽいものだけスコア
    for c in cands:
        if c.japan_presence == "unlikely":
            j = llm_score_and_email(c)
            c.score = int(j.get("score", 0))
            c.rationale = j.get("rationale_jp","")
            c.email_en = j.get("email_en","")

    top = sorted(cands, key=lambda x: x.score, reverse=True)[:3]
    print("\n=== TOP 3 ===")
    for i, c in enumerate(top, 1):
        print(f"\n[{i}] score={c.score} japan={c.japan_presence}")
        print(c.title)
        print(c.url)
        print("理由:", c.rationale)
        print("---- email(en) ----")
        print(c.email_en)

if __name__ == "__main__":
    main()
