import os, json, re, time
import os

def _load_persona_from_env():
  core=os.environ.get("CORE_PERSONA_FILE")
  role=os.environ.get("PERSONA_FILE")
  t=[]
  if core and os.path.exists(core):
    t.append(open(core,"r",encoding="utf-8").read().strip())
  if role and os.path.exists(role):
    t.append(open(role,"r",encoding="utf-8").read().strip())
  return "\n\n".join([x for x in t if x])

PERSONA=_load_persona_from_env()

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

# --- Characters ---
SCOUT = ("スカウン", "さすらいの旅人（男/30代）")
JAP = ("ジャパチェ", "フランクな市場調査（男/50代）")
SCORE = ("イインデスカ", "利益判定のお局（女/50代）")
OUT = ("タノシ", "熱血営業マン（男/40代）")
REPORT = ("ヤルデ", "20代の天才（総括）")

def say(who, text):
    name, persona = who
    print(f"\n{name}（{persona}）\n{text}")

@dataclass
class Candidate:
    source: str
    title: str
    url: str
    summary: str
    japan_presence: str = "unknown"
    score: int = 0
    rationale: str = ""
    email_en: str = ""

def fetch_hn(n=20) -> List[Candidate]:
    feed = feedparser.parse("https://hnrss.org/frontpage")
    items = feed.entries[:n]
    out = []
    for it in items:
        out.append(Candidate(
            source="HackerNews",
            title=(it.get("title","") or "")[:200],
            url=it.get("link",""),
            summary=re.sub(r"\s+"," ", it.get("summary","") or "")[:400],
        ))
    return out

def ddg_collect_domains(query: str) -> list[str]:
    url = f"https://duckduckgo.com/?q={quote_plus(query)}"
    domains = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(20000)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
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

    uniq, seen = [], set()
    for d in domains:
        if d in seen:
            continue
        seen.add(d)
        uniq.append(d)
    return uniq

def japan_presence_check(title: str) -> str:
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

def should_skip_for_exclusive(c: Candidate) -> bool:
    # 独占販売に向かないものを最初から弾く（軽量フィルタ）
    t = (c.title + " " + c.url).lower()
    blacklist = [
        "cnn.com", "bbc.co.uk", "nytimes.com", "reuters.com", "scripps.edu",
        "paper", "study", "research", "clinical", "fentanyl", "opioid",
        "github.com", "gitlab.com", "arxiv.org"
    ]
    return any(b in t for b in blacklist)

def llm_score_and_email(c: Candidate) -> dict:
    prompt = f"""
You are evaluating products/startups for Japan-exclusive distribution opportunities.
We want deals that can realistically become "exclusive distributor / reseller / agency" in Japan.
Avoid regulated medicine/medical claims, avoid pure OSS without clear commercial offer.
Return ONLY JSON:
{{
  "score": <0-100 integer>,
  "rationale_jp": "<2-4 lines Japanese rationale>",
  "email_en": "<short English outreach email proposing Japan-exclusive distributor discussion>"
}}
Candidate:
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
    say(REPORT, "🧠 会議開始。目的：海外ネタ→日本未上陸→独占販売アプローチ候補を3件に絞る。")

    # Scout
    say(SCOUT, "……風の匂いが変わった。今日の“まだ日本にない宝”を拾ってくる。")
    cands = fetch_hn(20)
    say(SCOUT, f"拾ったネタは {len(cands)} 件。まずは雑音（ニュース/研究/OSS）を弾く。")

    cands = [c for c in cands if c.url and not should_skip_for_exclusive(c)]
    say(SCOUT, f"独占向き候補に残ったのは {len(cands)} 件。")

    # Japan checker
    say(JAP, "よし、既に日本で出回ってる気配があるかザクっと見るわ。")
    for c in cands:
        time.sleep(1.0)
        c.japan_presence = japan_presence_check(c.title)

    # Scoring
    say(SCORE, "はい、儲かる可能性で切るわよ。低いのは容赦なく落とす。")
    for c in cands:
        if c.japan_presence == "unlikely":
            j = llm_score_and_email(c)
            c.score = int(j.get("score", 0))
            c.rationale = j.get("rationale_jp","")
            c.email_en = j.get("email_en","")

    top = sorted([c for c in cands if c.japan_presence == "unlikely"], key=lambda x: x.score, reverse=True)[:3]

    if not top:
        say(REPORT, "今日は“独占向き”が薄い。次は情報源をKickstarter/PH寄りにするのが正解。")
        return

    for i, c in enumerate(top, 1):
        say(SCORE, f"【候補{i}】Score={c.score}\n{c.title}\n{c.url}\n理由：\n{c.rationale}")

    # Outreach
    say(OUT, "よっしゃ！刺さる形に整えて、すぐ送れる状態にする！")
    for i, c in enumerate(top, 1):
        say(OUT, f"【候補{i}：英語メール案】\n{c.email_en}")

    # Report
    say(REPORT, "✅ 本日の結論：上位3件を“送信候補”として保存。次はKickstarter等のソース追加で当たり率を上げる。")

if __name__ == "__main__":
    main()
