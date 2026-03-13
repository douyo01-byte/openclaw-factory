import json
import os
import time
from pathlib import Path

STATE = Path("obs/db_integrity_state.json")
LAST = Path("obs/db_integrity_watchdog_last.json")
SEND_INTERVAL = 600

def tg_send(text):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not chat:
        return
    import requests
    requests.post(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data={"chat_id": chat, "text": text},
        timeout=20,
    ).raise_for_status()

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def main():
    state = load_json(STATE, {})
    last = load_json(LAST, {})

    anomaly = int(state.get("lifecycle_anomaly_count", 0) or 0)
    last_anomaly = int(last.get("anomaly", 0) or 0)
    last_sent_at = int(last.get("last_sent_at", 0) or 0)
    now = int(time.time())

    LAST.parent.mkdir(parents=True, exist_ok=True)

    if anomaly <= 0:
        LAST.write_text(
            json.dumps({"anomaly": 0, "last_sent_at": last_sent_at}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("[watchdog] suppress lifecycle notification because anomaly=0", flush=True)
        return

    if last_anomaly != anomaly or now - last_sent_at >= SEND_INTERVAL:
        text = f"⚠ OpenClaw DB整合性異常\nlifecycle anomaly={anomaly}"
        tg_send(text)
        LAST.write_text(
            json.dumps({"anomaly": anomaly, "last_sent_at": now}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[watchdog] sent anomaly={anomaly}", flush=True)
        return

    print(f"[watchdog] skip anomaly={anomaly} cooldown={now - last_sent_at}s", flush=True)

if __name__ == "__main__":
    main()
