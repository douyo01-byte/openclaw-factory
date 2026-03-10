from __future__ import annotations
import os, json, time, sqlite3
import requests

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = os.path.expanduser("~/AI/openclaw-factory-daemon/data/dev_merge_notify_v1.state")
SLEEP = int(os.environ.get("DEV_MERGE_NOTIFY_SLEEP", "20"))
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

def tg_send(text: str):
    if not TG_TOKEN or not TG_CHAT:
        print("[merge_notify] telegram env missing", flush=True)
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": text},
        timeout=(3, 20),
    ).raise_for_status()

def load_last_id() -> int:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return int((f.read() or "0").strip() or "0")
    except Exception:
        return 0

def save_last_id(v: int):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        f.write(str(v))

def build_msg(row: sqlite3.Row) -> str:
    title = (row["title"] or "").replace("統  合  完  了  : ", "").replace("統 合 完 了 : ", "").strip()
    pr_url = (row["pr_url"] or "").strip()
    pid = row["proposal_id"]
    out = []
    out.append("🚀 開発完了")
    out.append(f"ID:{pid}")
    out.append(f"案件:{title or '不明'}")
    out.append("")
    out.append("【結果】")
    out.append("・main への統合が完了")
    out.append("・学習ループへ接続可能")
    if pr_url:
        out.append("")
        out.append("【PR】")
        out.append(pr_url)
    return "\n".join(out)

def main():
    while True:
        try:
            last_id = load_last_id()
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                select id, event_type, proposal_id, title, coalesce(pr_url,'') pr_url
                from ceo_hub_events
                where event_type='merged' and id>?
                order by id asc
            """, (last_id,)).fetchall()
            new_last = last_id
            for r in rows:
                msg = build_msg(r)
                tg_send(msg)
                new_last = int(r["id"])
                print(f"[merge_notify] sent event_id={new_last} proposal_id={r['proposal_id']}", flush=True)
            conn.close()
            if new_last != last_id:
                save_last_id(new_last)
        except Exception as e:
            print(f"[merge_notify] error {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
