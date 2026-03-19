import json
import os
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE = Path("obs/db_integrity_watchdog_last.json")

def tg_send(text):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not tok or not chat:
        print("[watchdog] telegram env missing", flush=True)
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode("utf-8")
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data=data,
            timeout=10,
        ) as r:
            r.read()
        return True
    except Exception as e:
        print(f"[watchdog] telegram send failed: {e}", flush=True)
        return False

def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    state = load_state()
    anomaly = 0
    detail = "ok"
    try:
        con = sqlite3.connect(DB, timeout=30)
        row = con.execute("pragma quick_check;").fetchone()
        con.close()
        detail = (row[0] if row and row[0] is not None else "unknown").strip()
        if detail.lower() != "ok":
            anomaly = int(state.get("anomaly", 0)) + 1
    except Exception as e:
        detail = f"exception: {e}"
        anomaly = int(state.get("anomaly", 0)) + 1

    last_detail = state.get("detail", "")
    last_anomaly = int(state.get("anomaly", 0))

    if anomaly > 0 and (detail != last_detail or anomaly != last_anomaly):
        sent = tg_send(f"DB integrity watchdog anomaly={anomaly}\nDB={DB}\ndetail={detail}")
        print(f"[watchdog] sent anomaly={anomaly} ok={sent}", flush=True)
    else:
        print(f"[watchdog] detail={detail} anomaly={anomaly}", flush=True)

    save_state({
        "db": DB,
        "detail": detail,
        "anomaly": anomaly
    })

if __name__ == "__main__":
    main()
