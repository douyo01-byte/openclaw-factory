import json, os, time
from pathlib import Path

STATE = Path("obs/db_integrity_state.json")
LAST = Path("obs/db_integrity_watchdog_last.json")
INTERVAL_SEC = 600

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return default

def tg_send(text):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not tok or not chat:
        return
    import requests
    requests.post(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data={"chat_id": chat, "text": text},
        timeout=20
    ).raise_for_status()

def main():
    cur = load_json(STATE, {})
    last = load_json(LAST, {})

    lifecycle = int(cur.get("lifecycle_anomaly_count", 0) or 0)
    pr_created_without_merged = int(cur.get("pr_created_without_merged", 0) or 0)
    merged_without_learning_result = int(cur.get("merged_without_learning_result", 0) or 0)
    status_mismatch = int(cur.get("status_mismatch", 0) or 0)

    anomaly = lifecycle + pr_created_without_merged + merged_without_learning_result + status_mismatch
    now = int(time.time())

    last_anomaly = int(last.get("anomaly", 0) or 0)
    last_sent_at = int(last.get("last_sent_at", 0) or 0)

    should_send = False
    if anomaly > 0:
        if last_anomaly <= 0:
            should_send = True
        elif now - last_sent_at >= INTERVAL_SEC:
            should_send = True

    if should_send:
        text = (
            "⚠ OpenClaw DB整合性異常\\n"
            f"lifecycle anomaly={lifecycle}\\n"
            f"pr_created_without_merged={pr_created_without_merged}\\n"
            f"merged_without_learning_result={merged_without_learning_result}\\n"
            f"status_mismatch={status_mismatch}"
        )
        tg_send(text)
        last = {"anomaly": anomaly, "last_sent_at": now}
        LAST.parent.mkdir(parents=True, exist_ok=True)
        LAST.write_text(json.dumps(last, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[watchdog] sent anomaly={anomaly}", flush=True)
        return

    if anomaly == 0:
        if last_anomaly > 0:
            print("[watchdog] suppress recovery notification", flush=True)
        last = {"anomaly": 0, "last_sent_at": last_sent_at}
        LAST.parent.mkdir(parents=True, exist_ok=True)
        LAST.write_text(json.dumps(last, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[watchdog] suppress lifecycle notification because mismatch_total=0", flush=True)
        return

    print(f"[watchdog] skip anomaly={anomaly} cooldown={now - last_sent_at}s", flush=True)

if __name__ == "__main__":
    main()
