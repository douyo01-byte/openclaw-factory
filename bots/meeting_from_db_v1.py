from typing import List, Tuple
from dataclasses import dataclass
import os
import sqlite3
from datetime import datetime
from oclibs.telegram import send as tg_send

from urllib.parse import urljoin, urlparse
import requests
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
JP_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
CONTACT_HINT_RE = re.compile(r"(contact|support|help|inquiry|お 問 い 合 わ せ |問 合 せ |問 い 合 わ せ )", re.IGNORECASE)
AMAZON_RAKUTEN_RE = re.compile(r"(amazon\.co\.jp|rakuten\.co\.jp|楽 天 |ア マ ゾ ン )", re.IGNORECASE)
PATH_CANDIDATES = ["/", "/contact", "/about", "/privacy", "/terms", "/company"]

def normalize_base(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    p = urlparse(u)
    if not p.scheme:
        u = "https://" + u
    return u

def fetch(url: str, timeout: int = 15):
    headers = {"User-Agent": "OpenClawResearch/1.0"}
    r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    return r.status_code, r.text or ""

def extract_signals(html: str):
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

def summarize(signals_by_path):
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

def scan_contact_paths(url: str, timeout: int = 10):
    base = normalize_base(url)
    if not base:
        return {
            "emails": [],
            "has_jp": False,
            "has_contact_hint": False,
            "has_amazon_rakuten": False,
            "ok_paths": [],
        }
    signals_by_path = []
    for path in PATH_CANDIDATES:
        try:
            u = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
            code, html = fetch(u, timeout=timeout)
            signals_by_path.append((path, code, extract_signals(html)))
        except Exception:
            signals_by_path.append((path, 0, {
                "emails": [],
                "has_jp": False,
                "has_contact_hint": False,
                "has_amazon_rakuten": False,
            }))
    return summarize(signals_by_path)

def enqueue_contact(conn: sqlite3.Connection, item_id: int, email: str, source: str) -> None:
    try:
        conn.execute(
            "INSERT INTO contacts(item_id, email, source, created_at) VALUES(?,?,?,datetime('now'))",
            (item_id, email, source),
        )
    except Exception:
        pass

def upsert_role_brief(conn: sqlite3.Connection, role: str, title: str, url: str, text: str) -> None:
    topic = (title or "unknown").strip()
    source_url = (url or "").strip()
    if not source_url:
        return
    summary = text
    conn.execute(
        "INSERT INTO role_briefs(role, topic, source_url, title, summary, fetched_at) "
        "VALUES(?,?,?,?,?,datetime('now')) "
        "ON CONFLICT(role,topic,source_url) DO UPDATE SET "
        "title=excluded.title, summary=excluded.summary, fetched_at=datetime('now')",
        ((role or "").strip(), topic, source_url, (title or "").strip(), summary),
    )

def collect_meeting_signals(top: List["Row"]) -> dict[int, dict]:
    out = {}
    for r in top:
        try:
            out[int(r.id)] = scan_contact_paths(r.url, timeout=10)
        except Exception:
            out[int(r.id)] = {
                "emails": [],
                "has_jp": False,
                "has_contact_hint": False,
                "has_amazon_rakuten": False,
                "ok_paths": [],
            }
    return out


def build_signal_line(sig: dict) -> str:
    emails = sig.get("emails") or []
    ok_paths = sig.get("ok_paths") or []
    return (
        f"signal: jp={'yes' if sig.get('has_jp') else 'no'} "
        f"contact_hint={'yes' if sig.get('has_contact_hint') else 'no'} "
        f"emails={len(emails)} "
        f"paths={','.join(ok_paths) if ok_paths else '-'}"
    )

def persist_meeting_outputs(conn: sqlite3.Connection, top: List["Row"], text: str, signal_map: dict[int, dict]) -> None:
    if top:
        upsert_role_brief(conn, "yarde", top[0].title, top[0].url, text)
    for r in top:
        sig = signal_map.get(int(r.id), {})
        for e in (sig.get("emails") or [])[:10]:
            enqueue_contact(conn, r.id, e, "meeting_signal")


def _fetch_item_meta(conn: sqlite3.Connection, item_id: int) -> tuple[str, int, str]:
    """Return (decision, priority, last_note_line). Missing -> ('-', 0, '')."""
    try:
        cur = conn.execute(
            "SELECT decision, priority, note FROM item_meta WHERE item_id=?",
            (item_id,),
        )
        row = cur.fetchone()
        if not row:
            return ("-", 0, "")
        decision, priority, note = row
        decision = (decision or "-").strip()
        try:
            priority = int(priority or 0)
        except Exception:
            priority = 0
        note = note or ""
        # noteは追記されているので「最後の非空行」を表示
        lines = [ln.strip() for ln in note.splitlines() if ln.strip()]
        last_note = lines[-1] if lines else ""
        # 長すぎる場合は短縮
        if len(last_note) > 60:
            last_note = last_note[:60] + "…"
        return (decision, priority, last_note)
    except Exception:
        return ("-", 0, "")


def _meta_line(conn: sqlite3.Connection, item_id: int) -> str:
    decision, priority, last_note = _fetch_item_meta(conn, item_id)
    note_part = f" note={last_note}" if last_note else ""
    return f"[meta] prio={priority} decision={decision}{note_part}"


DB = "data/openclaw.db"


def fetch_pool_rows(conn: sqlite3.Connection, limit: int):
    cur = conn.cursor()
    return cur.execute(
        '''
        SELECT id,
               COALESCE(title,'(no title)') as title,
               COALESCE(url,'') as url,
               COALESCE(source,'unknown') as source,
               COALESCE(status,'unknown') as status
        FROM items
        WHERE status IN ('new','review')
        ORDER BY id DESC
        LIMIT ?
        ''',
        (limit,),
    ).fetchall()

@dataclass
class Row:
    id: int
    title: str
    url: str
    source: str
    status: str


def fetch_pool(limit=60) -> List[Row]:
    conn = sqlite3.connect(DB)
    rows = fetch_pool_rows(conn, limit)
    conn.close()
    return [Row(*r) for r in rows]

def pick_top(pool, k=10):
    return pool[:k]

def load_meeting_candidates(limit: int = 60, k: int = 10) -> List[Row]:
    return pick_top(fetch_pool(limit=limit), k=k)


def short_kind(url: str) -> str:
    u = (url or "").lower()
    if "github.com" in u:
        return "GitHub"
    if "producthunt.com" in u:
        return "ProductHunt"
    if "reddit.com" in u:
        return "Reddit"
    if u.startswith("http"):
        return "Web"
    return "Other"


def action_plan(r: Row) -> str:
    kind = short_kind(r.url)
    if kind == "GitHub":
        return "→ README/Websiteリンク抽出 → 公式サイト → contact/email"
    if kind == "Reddit":
        return "→ 投稿本文の外部URL → 公式/販売サイト → contact/email"
    if kind == "ProductHunt":
        return "→ 製品サイト → contact/email（無ければ company_finder）"
    if kind == "Web":
        return "→ /contact /about 優先クロール → email or フォームURL保存"
    return "→ まず公式サイト特定"


def fetch_role_briefs(role: str, n: int = 2) -> List[Tuple[str, str, str]]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT COALESCE(title,''), COALESCE(source_url,''), COALESCE(summary,'')
        FROM role_briefs
        WHERE role=?
        ORDER BY fetched_at DESC, id DESC
        LIMIT ?
    """,
        (role, n),
    ).fetchall()
    conn.close()
    return [(t, u, s) for (t, u, s) in rows if t and u]


def make_rule(role: str, brief_title: str, brief_summary: str) -> str:
    """
    “学習→ルール化”の雑変換（後でLLM要約に差し替え可能）
    """
    s = (brief_summary or "").lower()
    t = (brief_title or "").lower()

    if role == "japache":
        if "amazon" in s or "marketplace" in s:
            return "新ルール：日本Amazon/楽天の有無を最優先で当たる（代理店より先に）"
        if "layoff" in t or "cuts" in t:
            return "新ルール：組織縮小/混乱中の企業は連絡先取れても優先度を下げる"
        return "新ルール：国内上陸の兆候（日本語LP/代理店表記）を先に探す"

    if role == "iindesuka":
        if "pricing" in s or "subscription" in s or "saas" in s:
            return "新ルール：価格ページが無いSaaSは“売り方不明”として減点"
        return "新ルール：単価×輸送×差別化の3点で即死判定"

    if role == "tanoshi":
        if "crm" in t or "pipeline" in s:
            return "新ルール：初手は『テスト輸入→反応→独占』の順で提案"
        if "cold" in s or "outreach" in s:
            return "新ルール：初手メールは3行（価値/理由/次の一歩）に固定"
        return "新ルール：メール無ければフォームでもOK、返信導線を最短化"

    if role == "scout":
        if "product hunt" in s or "launch" in s or "release" in s:
            return "新ルール：ローンチ直後は“公式サイトのContact”が出やすいので即回収"
        return "新ルール：プラットフォームURLは必ず外部リンク（公式）まで辿ってから評価"

    return "新ルール：学習を判断基準に反映する"


def meeting_text(top: List[Row], signal_map: dict[int, dict]) -> str:
    conn = sqlite3.connect(os.environ.get("OCLAW_DB_PATH", "./data/openclaw.db"))
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = []

        lines.append("🧠 ヤルデ（20代の天才/総括）")
        lines.append(
            f"会議開始（{now}）。目的：海外候補 → 日本未上陸っぽい → 連絡先取得まで一気通貫。"
        )
        lines.append(
            "今日のゴール：『連絡先（メール or フォーム）』を最低3件、DBに積む。\n"
        )

        lines.append(
            "📚 学習ログ（各自が空き時間に仕入れたネタ → 今日から使う新ルール）"
        )
        for role, label in [
            ("scout", "🌍 スカウン"),
            ("japache", "🕵️ ジャパチェ"),
            ("iindesuka", "💰 イインデスカ"),
            ("tanoshi", "🔥 タノシ"),
        ]:
            briefs = fetch_role_briefs(role, n=2)
            if briefs:
                # 最新1件をルール化
                rule = make_rule(role, briefs[0][0], briefs[0][2])
                lines.append(f"{label}：{rule}")
                # 学習ネタも2件だけ添付
                for t, u, _s in briefs:
                    lines.append(f" - {t} / {u}")
            else:
                lines.append(f"{label}：新ルールなし（まだ学習メモなし）")
        lines.append("")

        lines.append("🌍 スカウン（さすらいの旅人/30代）")
        lines.append(
            "……旅の途中で拾った“宝”を並べる。今日は上位10件。『売れ筋』じゃなく『攻め筋』で選んだ。\n"
        )

        for i, r in enumerate(top, 1):
            # injected: show human meta
            lines.append(_meta_line(conn, r.id))
            kind = short_kind(r.url)
            lines.append(f"【候補{i}】({r.status}/{kind})")
            lines.append(r.title)
            lines.append(r.url)
            sig = signal_map.get(int(r.id), {})
            signal_line = build_signal_line(sig)
            if signal_line:
                lines.append(signal_line)
            lines.append(f"次アクション {action_plan(r)}\n")

        lines.append("🧠 ヤルデ（総括/決裁）")
        lines.append("✅ 本日の決裁：この10件は review 継続。連絡先探索を回す。")
        lines.append("担当割り当て：")
        lines.append("・スカウン：Reddit/GitHubの外部リンク（公式）を確定")
        lines.append("・ジャパチェ：日本上陸チェック（Amazon/楽天/代理店）")
        lines.append("・イインデスカ：利益/サイズ/単価の即死判定")
        lines.append("・タノシ：取れた連絡先から“最短で返事が来る初手文面”を準備")
        lines.append("次回の勝ち条件：連絡先DB +3（メール優先、無ければフォームURL）。")

        return "\n".join(lines)

    finally:
        conn.close()



def dispatch_meeting(conn: sqlite3.Connection, top: List["Row"]) -> str:
    signal_map = collect_meeting_signals(top)
    text = meeting_text(top, signal_map)
    persist_meeting_outputs(conn, top, text, signal_map)
    return text

def run_meeting_once(top: List["Row"]) -> str:
    conn = sqlite3.connect(os.environ.get("OCLAW_DB_PATH", "./data/openclaw.db"))
    try:
        text = dispatch_meeting(conn, top)
        conn.commit()
        return text
    finally:
        conn.close()

def render_meeting_fallback(top: List["Row"]) -> str:
    return meeting_text(top, collect_meeting_signals(top))

def main():
    top = load_meeting_candidates(limit=60, k=10)
    try:
        text = run_meeting_once(top)
    except Exception:
        text = render_meeting_fallback(top)
    tg_send(text)
    print("meeting sent")


if __name__ == "__main__":
    main()
