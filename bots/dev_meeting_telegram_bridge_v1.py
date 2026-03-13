from __future__ import annotations
import json
import os
import sqlite3
import time
from pathlib import Path
import requests

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = Path(os.path.expanduser("~/AI/openclaw-factory-daemon/data/dev_meeting_telegram_bridge_v1.state"))
SLEEP = int(os.environ.get("DEV_MEETING_BRIDGE_SLEEP", "15"))

TG_TOKEN = (os.environ.get("TELEGRAM_OPS_BOT_TOKEN") or os.environ.get("TELEGRAM_ROUTING_BOT_TOKEN") or os.environ.get("TELEGRAM_03_BOT_TOKEN") or os.environ.get("TELEGRAM_REPORT_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_OPS_CHAT_ID") or os.environ.get("TELEGRAM_ROUTING_CHAT_ID") or os.environ.get("TELEGRAM_03_CHAT_ID") or os.environ.get("TELEGRAM_REPORT_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

WATCH_TYPES = {"ai_meeting", "learning_result", "ai_employee"}

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

def get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"pragma table_info({table})").fetchall()
    return {str(r[1]) for r in rows}

def short(s: str, n: int = 500) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "..."

def extract_detail(row: sqlite3.Row, cols: set[str]) -> str:
    for k in ["summary", "detail", "content", "body", "note", "message"]:
        if k in cols:
            v = row[k]
            if v:
                return short(str(v), 700)
    if "payload_json" in cols and row["payload_json"]:
        try:
            obj = json.loads(row["payload_json"])
            if isinstance(obj, dict):
                for k in ["summary", "detail", "content", "body", "note", "message"]:
                    v = obj.get(k)
                    if v:
                        return short(str(v), 700)
            return short(json.dumps(obj, ensure_ascii=False), 700)
        except Exception:
            return short(str(row["payload_json"]), 700)
    return ""

def icon_for(t: str) -> str:
    if t == "ai_meeting":
        return "🧠"
    if t == "learning_result":
        return "📘"
    if t == "ai_employee":
        return "👤"
    return "📌"

def label_for(t: str) -> str:
    if t == "ai_meeting":
        return "AI会議"
    if t == "learning_result":
        return "学習反映"
    if t == "ai_employee":
        return "AI社員"
    return t

def build_msg(row: sqlite3.Row, cols: set[str]) -> str:
    event_type = str(row["event_type"] or "")
    title = str(row["title"] or "").strip()
    created_at = str(row["created_at"] or "").strip()
    detail = extract_detail(row, cols)

    lines = [
        f"{icon_for(event_type)} OpenClaw {label_for(event_type)}",
        f"件名: {title or '(no title)'}",
    ]
    if created_at:
        lines.append(f"時刻: {created_at}")
    if detail:
        lines += ["", detail]
    return "\n".join(lines).strip()

def main():
    while True:
        try:
            last_id = load_last_id()
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("pragma busy_timeout=30000")
            cols = get_columns(conn, "ceo_hub_events")
            rows = conn.execute("""
                select *
                from ceo_hub_events
                where id > ?
                order by id asc
            """, (last_id,)).fetchall()
            new_last = last_id
            for r in rows:
                new_last = int(r["id"])
                event_type = str(r["event_type"] or "")
                if event_type not in WATCH_TYPES:
                    continue
                msg = build_msg(r, cols)
                tg_send(msg)
                print(f"[meeting_bridge] sent event_id={new_last} type={event_type}", flush=True)
            conn.close()
            if new_last != last_id:
                save_last_id(new_last)
        except Exception as e:
            print(f"[meeting_bridge] error {e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
