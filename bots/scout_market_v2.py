import json
import time
import sqlite3
import hashlib
import os


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
from typing import List, Dict, Any
import feedparser


def save_item(conn, url: str, title: str, source: str):
    """
    items に upsert（urlユニーク）
    """
    conn.execute(
        """
        INSERT INTO items (url, title, source, first_seen_at, last_seen_at, status)
        VALUES (?, ?, ?, datetime('now'), datetime('now'), 'new')
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title,
            source=excluded.source,
            last_seen_at=datetime('now')
        """,
        (url, title, source),
    )


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from oclibs.telegram import send as tg_send
from oclibs.contact_finder import find_contacts
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

DB_PATH = "data/openclaw.db"
SOURCES_PATH = "configs/sources.json"


@dataclass
class Item:
    source: str
    title: str
    url: str
    published: str = ""
    score: int = 0
    rationale_jp: str = ""
    emails: List[str] = None
    contact_pages: List[str] = None
    notes: str = ""


def db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS seen (key TEXT PRIMARY KEY, url TEXT, title TEXT, source TEXT, ts INTEGER)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS contacts (url TEXT PRIMARY KEY, emails TEXT, pages TEXT, notes TEXT, ts INTEGER)"
    )
    conn.commit()
    return conn, cur


def key_for(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def is_seen(cur, k: str) -> bool:
    cur.execute("SELECT 1 FROM seen WHERE key=?", (k,))
    return cur.fetchone() is not None


def mark_seen(cur, it: Item):
    cur.execute(
        "INSERT OR IGNORE INTO seen(key,url,title,source,ts) VALUES(?,?,?,?,strftime('%s','now'))",
        (key_for(it.url), it.url, it.title, it.source),
    )


def save_contacts(cur, it: Item):
    cur.execute(
        "INSERT OR REPLACE INTO contacts(url,emails,pages,notes,ts) VALUES(?,?,?,?,strftime('%s','now'))",
        (
            it.url,
            json.dumps(it.emails or []),
            json.dumps(it.contact_pages or []),
            it.notes or "",
        ),
    )


def load_sources() -> List[Dict[str, Any]]:
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["sources"]


def fetch_rss(source_name: str, url: str, limit=20) -> List[Item]:
    d = feedparser.parse(url)
    out = []
    for e in d.entries[:limit]:
        link = getattr(e, "link", "") or ""
        title = getattr(e, "title", "") or ""
        published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
        if link and title:
            out.append(
                Item(
                    source=source_name,
                    title=title.strip(),
                    url=link.strip(),
                    published=published,
                )
            )
    return out


def llm_score(it: Item) -> Dict[str, Any]:
    """
    0-100点:
      - ガジェット/家電/物理プロダクト寄り +20
      - 日本未上陸っぽい +20（確証不要、推定で）
      - 卸/独占に向く（単価・差別化・供給） +30
      - 法規制/危険物/医療/薬物系は減点
    """
    prompt = f"""
あなたは海外プロダクトの日本独占販売候補を評価する担当（イインデスカ）です。
対象は「クラファン・ガジェット/家電寄り」を優先。ただしカテゴリは完全固定しない。

次の候補を0〜100で採点し、短い日本語理由を1〜2文で書いてください。
危険物・違法性・薬機法リスクが高い/医療薬物系は減点してください。

タイトル: {it.title}
URL: {it.url}

出力はJSONのみ:
{{"score": 0, "rationale_jp": "..." }}
"""
    r = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2
    )
    txt = r.choices[0].message.content.strip()
    # ざっくりJSON抽出
    try:
        return json.loads(txt)
    except Exception:
        # 失敗時の保険
        return {"score": 0, "rationale_jp": txt[:200]}


def format_tg(items: List[Item]) -> str:
    msg = "🧭 <b>Scout Report</b>（候補→連絡先まで）\n"
    msg += f"件数: {len(items)}\n\n"
    for i, it in enumerate(items[:8], 1):
        msg += f"【{i}】Score={it.score}\n"
        msg += f"{it.title}\n{it.url}\n"
        if it.rationale_jp:
            msg += f"理由: {it.rationale_jp}\n"
        if it.emails:
            msg += "Emails: " + ", ".join(it.emails) + "\n"
        if it.contact_pages:
            msg += "Contact: " + " | ".join(it.contact_pages[:2]) + "\n"
        if it.notes:
            msg += f"Note: {it.notes}\n"
        msg += "\n"
    return msg


def format_meeting(top):
    lines = []
    lines.append(
        "ヤルデ（20代の天才/総括）\n🧠 会議開始。目的：海外候補→日本未上陸っぽい→連絡先取得まで。\n"
    )
    lines.append(
        "スカウン（さすらいの旅人/30代）\n……旅の途中で拾った“宝”を並べる。今日は上位10件。\n"
    )
    lines.append(
        "ジャパチェ（市場調査/50代）\n日本で既に売ってそうか、匂いで当たりをつけるぞ。\n"
    )
    lines.append(
        "イインデスカ（利益判定/50代）\nはい、儲からないのは落とすわよ。ガジェット/家電寄り優先。\n"
    )

    for i, it in enumerate(top, 1):
        score = getattr(it, "score", "-")
        lines.append(f"【候補{i}】Score={score}\n{it.title}\n{it.url}\n")
        emails = getattr(it, "emails", None)
        if emails:
            lines.append(
                "連絡先(候補): "
                + ", ".join(emails[:5])
                + ("\n" if len(emails) <= 5 else " ...\n")
            )

    lines.append(
        "タノシ（熱血営業/40代）\nよっしゃ！ 連絡先が取れたやつから次の一手を整える！\n"
    )
    lines.append(
        "ヤルデ（20代の天才/総括）\n✅ 本日の結論：候補をDBに保存。次は公式サイトへ辿って“本物の連絡先”を抜く。\n"
    )
    return "\n".join(lines)


def main():
    conn, cur = db()
    sources = load_sources()

    # 収集（seenは飛ばす）
    pool: List[Item] = []
    for s in sources:
        if s.get("kind") == "rss":
            items = fetch_rss(s["name"], s["url"], limit=20)
            for it in items:
                if not is_seen(cur, key_for(it.url)):
                    pool.append(it)

    # 上限（暴走防止）
    pool = pool[:40]
    print("Collected new candidates:", len(pool))

    # 採点（LLM）
    for it in pool:
        time.sleep(0.6)  # 優しめ
        j = llm_score(it)
        it.score = int(j.get("score", 0) or 0)
        it.rationale_jp = (j.get("rationale_jp", "") or "")[:200]

    # 上位だけ連絡先抽出（重いので絞る）
    top = sorted(pool, key=lambda x: x.score, reverse=True)[:10]

    for it in top:
        time.sleep(0.7)
        c = find_contacts(it.url)
        it.emails = c.get("emails", [])
        it.contact_pages = c.get("contact_pages", [])
        it.notes = c.get("notes", "")

        mark_seen(cur, it)
        save_contacts(cur, it)
        conn.commit()

    if top:

        # --- AUTO-SAVE to SQLite (AUTO-ADD) ---
        for it in top:
            save_item(conn, it.url, it.title, it.source)
        conn.commit()

        tg_send(format_meeting(top))
        print("Sent to Telegram:", len(top))
    else:
        print("No new items")

    conn.close()


if __name__ == "__main__":
    main()


# --- DB helpers (AUTO-ADD) ---
