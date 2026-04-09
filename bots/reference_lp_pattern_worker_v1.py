#!/usr/bin/env python3
from __future__ import annotations
import os
import re
import sqlite3
import sys
from pathlib import Path

DB = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H_RE = re.compile(r"<h([1-3])[^>]*>(.*?)</h\1>", re.I | re.S)
BTN_RE = re.compile(r"<(a|button)[^>]*>(.*?)</(a|button)>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
BAD_CHAR_RE = re.compile(r"[ÃÂ�]|â|ï¼|ã|ã|ã|é|æ|å|ç")
JP_RE = re.compile(r"[ぁ-んァ-ヶ一-龥]")
ALNUM_RE = re.compile(r"[A-Za-z0-9]")

NOISE_EXACT = {
    "-->",
    "BUY",
    "Instagram",
    "OFFICIAL SITE",
    "探す",
    "もっと知る",
    "Point 01",
    "Point 02",
    "Point 03",
    "タイプ",
    "業種･ジャンル",
    "特徴･スタイル",
    "色･配色",
    "書体",
    "動きの度合い･技術",
    "レイアウト･その他",
}

NOISE_PARTS = [
    "sankou design",
    "category",
    "カテゴリ",
    "アイテムを探す",
    "カテゴリーから探す",
    "サポートメニュー",
    "対応店舗",
    "店舗リスト",
    "ログイン",
    "会員登録",
    "カート",
    "メニュー",
    "menu",
    "studio",
    "framer",
    "nocode",
    "mobilefirst",
    "contentpage",
    "corporatesite",
    "brandsite",
    "webサイト",
    "lp（ランディングページ）",
    "official site",
    "instagram",
    "x.com",
    "facebook",
]

CTA_ALLOW_PARTS = [
    "詳しく",
    "見る",
    "読む",
    "購入",
    "申し込",
    "試す",
    "体験",
    "チェック",
    "確認",
    "予約",
    "相談",
    "応募",
    "商品",
    "公式",
]

def conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    try:
        con.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return con

def html_unescape_min(s: str) -> str:
    return (
        (s or "")
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&ndash;", " - ")
        .replace("&mdash;", " - ")
    )

def clean(s: str) -> str:
    s = TAG_RE.sub(" ", s or "")
    s = html_unescape_min(s)
    s = s.replace("\u3000", " ")
    s = SPACE_RE.sub(" ", s).strip(" 　\t\r\n-:/|")
    return s

def bad_text(s: str) -> bool:
    t = clean(s)
    if not t:
        return True
    if BAD_CHAR_RE.search(t):
        return True
    if len(t) <= 1:
        return True
    return False

def is_noise(s: str) -> bool:
    t = clean(s)
    tl = t.lower()
    if not t:
        return True
    if t in NOISE_EXACT:
        return True
    if any(x in tl for x in NOISE_PARTS):
        return True
    if bad_text(t):
        return True
    return False

def meaningful_heading(s: str) -> bool:
    t = clean(s)
    if is_noise(t):
        return False
    if len(t) < 4 or len(t) > 42:
        return False
    if t.count(" ") > 8:
        return False
    if not (JP_RE.search(t) or ALNUM_RE.search(t)):
        return False
    return True

def meaningful_cta(s: str) -> bool:
    t = clean(s)
    tl = t.lower()
    if is_noise(t):
        return False
    if len(t) < 3 or len(t) > 28:
        return False
    if t.isupper() and len(t) <= 5:
        return False
    if not any(x in t for x in CTA_ALLOW_PARTS) and not any(x in tl for x in ["buy now", "shop now", "learn more", "view more"]):
        return False
    return True

def fetch_jobs(c: sqlite3.Cursor, limit: int) -> list[sqlite3.Row]:
    return c.execute("""
        select *
        from conversation_jobs
        where coalesce(current_phase,'')='reference_lp_expanded'
        order by id asc
        limit ?
    """, (limit,)).fetchall()

def fetch_sources(c: sqlite3.Cursor, job_id: int) -> list[sqlite3.Row]:
    return c.execute("""
        select *
        from reference_lp_sources
        where job_id=?
          and coalesce(status,'')='done'
          and coalesce(parent_source_id,0) > 0
        order by id asc
    """, (job_id,)).fetchall()

def extract_title(html: str) -> str:
    m = TITLE_RE.search(html or "")
    t = clean(m.group(1)) if m else ""
    if is_noise(t):
        return ""
    return t[:120]

def extract_heads(html: str, limit: int = 20) -> list[str]:
    out = []
    seen = set()
    for _, raw in H_RE.findall(html or ""):
        t = clean(raw)
        if not meaningful_heading(t):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= limit:
            break
    return out

def extract_ctas(html: str, limit: int = 12) -> list[str]:
    out = []
    seen = set()
    for _, raw, _ in BTN_RE.findall(html or ""):
        t = clean(raw)
        if not meaningful_cta(t):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= limit:
            break
    return out

def dedupe_keep_order(items: list[str], limit: int) -> list[str]:
    out = []
    seen = set()
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
        if len(out) >= limit:
            break
    return out

def save_artifact(c: sqlite3.Cursor, job_id: int, body: str) -> None:
    c.execute("""
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
    """, (job_id, "reference_lp_pattern", "reference_lp_pattern", body, "", 1))

def build_body(job_id: int, rows: list[dict]) -> str:
    lines = []
    lines.append(f"# 参考LP構造学習 job {job_id}")
    lines.append("## 学習対象")
    for i, r in enumerate(rows, start=1):
        title = r["title"] or r["url"]
        lines.append(f"{i}. {title}")
        lines.append(f"   - {r['url']}")
    lines.append("")
    lines.append("## 共通見出しパターン")
    all_heads = []
    for r in rows:
        all_heads.extend(r["heads"][:5])
    common = dedupe_keep_order(all_heads, 20)
    for i, h in enumerate(common, start=1):
        lines.append(f"{i}. {h}")
    lines.append("")
    lines.append("## CTAパターン")
    all_cta = []
    for r in rows:
        all_cta.extend(r["ctas"][:3])
    ctas = dedupe_keep_order(all_cta, 12)
    for i, x in enumerate(ctas, start=1):
        lines.append(f"{i}. {x}")
    lines.append("")
    lines.append("## educate B へ移植する指針")
    lines.append("- FVは悩み直撃で、1文目で仕上がり価値を伝える")
    lines.append("- 商品画像を大きく置き、コピー量は絞る")
    lines.append("- 構成は 悩み → 仕上がり価値 → 成分根拠 → 使用イメージ → CTA")
    lines.append("- CTAは説明より行動を促す文言を優先する")
    lines.append("- セクションごとに1メッセージで切り、縦に流れる構成へ寄せる")
    lines.append("")
    lines.append("## 参考LP別メモ")
    for r in rows[:10]:
        lines.append(f"### {r['title'] or r['url']}")
        lines.append(f"- URL: {r['url']}")
        if r["heads"]:
            lines.append(f"- 見出し例: {' / '.join(r['heads'][:4])}")
        if r["ctas"]:
            lines.append(f"- CTA例: {' / '.join(r['ctas'][:3])}")
    return "\n".join(lines).strip()

def run_once(limit: int = 5) -> None:
    con = conn()
    c = con.cursor()
    rows = fetch_jobs(c, limit)
    done = 0
    for job in rows:
        try:
            sources = fetch_sources(c, job["id"])
            if not sources:
                continue
            parsed = []
            for s in sources:
                p = Path(s["local_path"])
                if not p.exists():
                    continue
                html = p.read_text(encoding="utf-8", errors="ignore")
                heads = extract_heads(html)
                ctas = extract_ctas(html)
                if not heads and not ctas:
                    continue
                parsed.append({
                    "url": s["source_url"],
                    "title": extract_title(html),
                    "heads": heads,
                    "ctas": ctas,
                })
            if not parsed:
                continue
            c.execute("""
                delete from conversation_artifacts
                where job_id=?
                  and artifact_type='reference_lp_pattern'
            """, (job["id"],))
            body = build_body(job["id"], parsed)
            save_artifact(c, job["id"], body)
            c.execute("""
                update conversation_jobs
                set current_phase='reference_lp_pattern_done',
                    updated_at=datetime('now')
                where id=?
            """, (job["id"],))
            print(f"reference_pattern_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"reference_pattern_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"reference_pattern_total={done}", flush=True)

def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_once(limit)

if __name__ == "__main__":
    main()
