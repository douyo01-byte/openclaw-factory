import json, os, time
from pathlib import Path

STATE = Path("obs/db_integrity_state.json")
LAST = Path("obs/db_integrity_watchdog_last.json")
LOG = Path("logs/db_integrity_watchdog_v1.log")

def tg_send(text):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID","").strip()
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
    except:
        return default

def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    state = load_json(STATE, {})
    last = load_json(LAST, {})

    lifecycle = int(state.get("lifecycle_anomaly_count", 0) or 0)
    mismatch = state.get("mismatch_counts", {}) or {}
    mismatch_total = sum(int(v or 0) for v in mismatch.values())

    payload = {
        "lifecycle_anomaly_count": lifecycle,
        "mismatch_total": mismatch_total,
        "mismatch_counts": mismatch,
        "pr_created_without_expected_status": int(state.get("pr_created_without_expected_status", 0) or 0),
        "missing_source_category_target_system": int(state.get("missing_source_category_target_system", 0) or 0),
    }

    changed = payload != last.get("payload")

    if changed:
        LAST.write_text(
            json.dumps({"checked_at": int(time.time()), "payload": payload}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    if mismatch_total <= 0:
        with LOG.open("a", encoding="utf-8") as f:
            f.write("[watchdog] suppress lifecycle notification because mismatch_total=0\n")
        return

    if not changed:
        with LOG.open("a", encoding="utf-8") as f:
            f.write("[watchdog] no_change\n")
        return

    lines = ["⚠ OpenClaw DB整合性異常"]
    for k, v in mismatch.items():
        v = int(v or 0)
        if v > 0:
            lines.append(f"{k}: {v}")
    tg_send("\n".join(lines))

if __name__ == "__main__":
    main()
