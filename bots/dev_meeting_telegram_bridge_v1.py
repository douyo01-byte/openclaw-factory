from __future__ import annotations
import os
import sqlite3
import time
from pathlib import Path
import requests

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = Path("data/dev_meeting_telegram_bridge_v1.state")
TG_TOKEN = (os.environ.get("TELEGRAM_OPS_BOT_TOKEN") or os.environ.get("TELEGRAM_ROUTING_BOT_TOKEN") or os.environ.get("TELEGRAM_03_BOT_TOKEN") or os.environ.get("TELEGRAM_REPORT_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_OPS_CHAT_ID") or os.environ.get("TELEGRAM_ROUTING_CHAT_ID") or os.environ.get("TELEGRAM_03_CHAT_ID") or os.environ.get("TELEGRAM_REPORT_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
SLEEP = int(os.environ.get("DEV_MEETING_BRIDGE_SLEEP", "20"))
MAX_ROWS_PER_TICK = int(os.environ.get("DEV_MEETING_BRIDGE_MAX_ROWS", "8"))
LEARNING_COOLDOWN_SEC = int(os.environ.get("DEV_MEETING_BRIDGE_LEARNING_COOLDOWN_SEC", "180"))
LEARNING_STATE_PATH = Path("data/dev_meeting_telegram_bridge_learning.state")

def load_last_id() -> int:
    try:
        return int(STATE_PATH.read_text(encoding="utf-8").strip() or "0")
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

def load_learning_state() -> dict[str, str]:
    try:
        raw = LEARNING_STATE_PATH.read_text(encoding="utf-8").splitlines()
        out = {}
        for line in raw:
            if "\t" in line:
                k, v = line.split("\t", 1)
                out[k] = v
        return out
    except Exception:
        return {}

def save_learning_state(d: dict[str, str]):
    LEARNING_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(f"{k}\t{v}" for k, v in d.items())
    LEARNING_STATE_PATH.write_text(text, encoding="utf-8")

def tg_send(text: str):
    if not TG_TOKEN or not TG_CHAT:
        raise RuntimeError("telegram env missing")
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": text},
        timeout=20,
    )
    r.raise_for_status()

def format_ai_employee(r: sqlite3.Row) -> str:
    title = (r["title"] or "").strip()
    body = (r["body"] or "").strip()
    created = (r["created_at"] or "").strip()
    return "\n".join([
        "👤 OpenClaw AI社員",
        f"件名: {title}",
        f"時刻: {created}",
        "",
        body or "内容なし",
    ])

def format_learning_result(r: sqlite3.Row) -> str:
    title = (r["title"] or "").strip()
    body = (r["body"] or "").strip()
    created = (r["created_at"] or "").strip()
    return "\n".join([
        "📘 OpenClaw 学習反映",
        f"件名: {title}",
        f"時刻: {created}",
        "",
        body or "内容なし",
    ])

def format_ai_meeting(r: sqlite3.Row) -> str:
    title = (r["title"] or "").strip()
    body = (r["body"] or "").strip()
    created = (r["created_at"] or "").strip()
    return "\n".join([
        "🧠 OpenClaw 定例会議",
        f"件名: {title}",
        f"時刻: {created}",
        "",
        body or "内容なし",
    ])

def should_send_learning(r: sqlite3.Row) -> bool:
    state = load_learning_state()
    title = (r["title"] or "").strip()
    created = (r["created_at"] or "").strip()
    key = title[:140]
    now = time.time()
    last = float(state.get(key, "0") or "0")
    if now - last < LEARNING_COOLDOWN_SEC:
        return False
    state[key] = str(now)
    if len(state) > 300:
        items = list(state.items())[-200:]
        state = dict(items)
    save_learning_state(state)
    return True

def build_message(r: sqlite3.Row) -> str | None:
    et = (r["event_type"] or "").strip()
    if et == "ai_employee":
        return format_ai_employee(r)
    if et == "ai_meeting":
        return format_ai_meeting(r)
    if et == "learning_result":
        if not should_send_learning(r):
            return None
        return format_learning_result(r)
    return None

def main():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=30000")
            last_id = clamp_last_id(conn, load_last_id())
            rows = conn.execute("""
                select id, event_type, title, body, created_at
                from ceo_hub_events
                where id > ?
                  and coalesce(event_type,'') in ('ai_meeting','ai_employee','learning_result')
                order by id asc
                limit ?
            """, (last_id, MAX_ROWS_PER_TICK)).fetchall()
            new_last = last_id
            for r in rows:
                msg = build_message(r)
                new_last = int(r["id"])
                if msg:
                    tg_send(msg)
                    print(f"[meeting_bridge] sent event_id={new_last} type={r['event_type']}", flush=True)
                else:
                    print(f"[meeting_bridge] skipped event_id={new_last} type={r['event_type']}", flush=True)
            conn.close()
            if new_last != last_id:
                save_last_id(new_last)
        except Exception as e:
            print(f"[meeting_bridge] error {e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
