from __future__ import annotations
import os
import sqlite3
import time
from pathlib import Path
import requests

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = Path(os.path.expanduser("~/AI/openclaw-factory-daemon/data/dev_meeting_telegram_bridge_v1.state"))
SLEEP = int(os.environ.get("DEV_MEETING_BRIDGE_SLEEP", "10"))
TG_TOKEN = (os.environ.get("TELEGRAM_OPS_BOT_TOKEN") or os.environ.get("TELEGRAM_ROUTING_BOT_TOKEN") or os.environ.get("TELEGRAM_03_BOT_TOKEN") or os.environ.get("TELEGRAM_REPORT_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_OPS_CHAT_ID") or os.environ.get("TELEGRAM_ROUTING_CHAT_ID") or os.environ.get("TELEGRAM_03_CHAT_ID") or os.environ.get("TELEGRAM_REPORT_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

def tg_send(text: str):
    if not TG_TOKEN or not TG_CHAT:
        print("[meeting_bridge] telegram env missing", flush=True)
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": text},
        timeout=(3, 20),
    ).raise_for_status()

def load_last_id() -> int:
    try:
        return int((STATE_PATH.read_text(encoding="utf-8").strip() or "0"))
    except Exception:
        return 0

def save_last_id(v: int):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(str(v), encoding="utf-8")

def clamp_last_id(conn: sqlite3.Connection, last_id: int) -> int:
    row = conn.execute("""
        select coalesce(max(id),0)
        from ceo_hub_events
        where coalesce(event_type,'') in ('ai_meeting','ai_employee','learning_result')
    """).fetchone()
    max_id = int((row[0] if row and row[0] is not None else 0))
    if last_id <= 0 and max_id > 0:
        save_last_id(max_id)
        print(f"[meeting_bridge] clamp last_id {last_id} -> {max_id}", flush=True)
        return max_id
    if max_id - last_id > 200:
        save_last_id(max_id)
        print(f"[meeting_bridge] fast_forward last_id {last_id} -> {max_id}", flush=True)
        return max_id
    return last_id

def short(s: str, n: int = 80) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "..."

def recent_meeting_context(conn: sqlite3.Connection, event_id: int):
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        select id, event_type, title, created_at
        from ceo_hub_events
        where id <= ?
          and coalesce(event_type,'') in ('learning_result','merged','pr_created','ai_employee')
        order by id desc
        limit 12
    """, (event_id,)).fetchall()
    return list(reversed(rows))

def build_ai_meeting(conn: sqlite3.Connection, r: sqlite3.Row) -> str:
    rows = recent_meeting_context(conn, int(r["id"]))
    merged = [x for x in rows if (x["event_type"] or "") == "merged"]
    prs = [x for x in rows if (x["event_type"] or "") == "pr_created"]
    learn = [x for x in rows if (x["event_type"] or "") == "learning_result"]
    emp = [x for x in rows if (x["event_type"] or "") == "ai_employee"]

    lines = []
    lines.append("🧠 OpenClaw AI会議")
    lines.append(f"件名: {r['title']}")
    lines.append(f"時刻: {r['created_at']}")
    lines.append("")
    lines.append(f"要点: merged={len(merged)} / pr_created={len(prs)} / learning={len(learn)} / ai_employee={len(emp)}")

    focus = []
    for x in (merged[-2:] + prs[-2:] + learn[-3:] + emp[-2:]):
        t = short(x["title"], 60)
        if t and t not in focus:
            focus.append(t)
    if focus:
        lines.append("")
        lines.append("今回の論点:")
        for t in focus[:6]:
            lines.append(f"- {t}")

    nexts = []
    if prs:
        nexts.append("PR作成済み案件の統合待ち確認")
    if merged:
        nexts.append("統合済み案件の学習反映監視")
    if learn:
        nexts.append("学習結果の次提案への転用")
    if emp:
        nexts.append("AI社員トピックの継続監視")
    if nexts:
        lines.append("")
        lines.append("次アクション:")
        for t in nexts[:4]:
            lines.append(f"- {t}")

    return "\n".join(lines)

def build_ai_employee(r: sqlite3.Row) -> str:
    return "\n".join([
        "👤 OpenClaw AI社員",
        f"件名: {r['title']}",
        f"時刻: {r['created_at']}",
        "",
        "AI社員トピックが更新されました。"
    ])

def build_learning(r: sqlite3.Row) -> str:
    return "\n".join([
        "📘 OpenClaw 学習反映",
        f"件名: {r['title']}",
        f"時刻: {r['created_at']}",
    ])

def build_default(r: sqlite3.Row) -> str:
    return "\n".join([
        "📎 OpenClaw イベント",
        f"種別: {r['event_type']}",
        f"件名: {r['title']}",
        f"時刻: {r['created_at']}",
    ])

def build_msg(conn: sqlite3.Connection, r: sqlite3.Row) -> str:
    et = (r["event_type"] or "").strip()
    if et == "ai_meeting":
        return build_ai_meeting(conn, r)
    if et == "ai_employee":
        return build_ai_employee(r)
    if et == "learning_result":
        return build_learning(r)
    return build_default(r)

def main():
    while True:
        try:
            last_id = load_last_id()
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("pragma busy_timeout=30000")
            last_id = clamp_last_id(conn, last_id)
            rows = conn.execute("""
                select id, event_type, title, created_at
                from ceo_hub_events
                where id > ?
                  and coalesce(event_type,'') in ('ai_meeting','ai_employee','learning_result')
                order by id asc
            """, (last_id,)).fetchall()
            new_last = last_id
            for r in rows:
                msg = build_msg(conn, r)
                tg_send(msg)
                new_last = int(r["id"])
                print(f"[meeting_bridge] sent event_id={new_last} type={r['event_type']}", flush=True)
            conn.close()
            if new_last != last_id:
                save_last_id(new_last)
        except Exception as e:
            print(f"[meeting_bridge] error {e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
