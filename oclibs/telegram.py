import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = (os.getenv("OCLAW_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID"))

TELEGRAM_MAX_LEN = 3900

def _split_telegram_message(text: str, limit: int = TELEGRAM_MAX_LEN):
    text = text or ""
    if len(text) <= limit:
        return [text]
    parts = []
    buf = text
    while len(buf) > limit:
        cut = buf.rfind("\n\n", 0, limit)
        if cut == -1:
            cut = buf.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunk = buf[:cut].rstrip()
        if chunk:
            parts.append(chunk)
        buf = buf[cut:].lstrip()
    if buf.strip():
        parts.append(buf.strip())
    return parts

def send(message: str):
  if _tg_dedupe(text):
    return
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram env missing (TELEGRAM_BOT_TOKEN + (OCLAW_TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID))")
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = _split_telegram_message(message)

    last_resp = None
    for ch in chunks:
        payload = {"chat_id": CHAT_ID, "text": ch}
        try:
            r = requests.post(url, json=payload, timeout=30)
            last_resp = r
            if r.status_code >= 400:
                print("Telegram send failed:", r.status_code, r.text[:200])
                return None
        except Exception as e:
            print("Telegram send error:", e)
            return None
        time.sleep(0.15)

    return last_resp

def send_with_buttons(text: str, buttons):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram env missing (TELEGRAM_BOT_TOKEN + (OCLAW_TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID))")
        return None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "reply_markup": {"inline_keyboard": buttons}}
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code >= 400:
            print("Telegram send failed:", r.status_code, r.text[:200])
            return None
        return r
    except Exception as e:
        print("Telegram send error:", e)
        return None

def _tg_dedupe(text: str) -> bool:
    return False
