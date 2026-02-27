from __future__ import annotations
import os
import requests

API_BASE = "https://api.telegram.org/bot{token}"

def _token() -> str:
    tok = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
    if not tok:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN (or BOT_TOKEN) env var")
    return tok

def get_updates(offset: int | None = None, timeout: int = 50):
    tok = _token()
    url = API_BASE.format(token=tok) + "/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(url, params=params, timeout=timeout + 10)
    r.raise_for_status()
    return r.json()

def send_message(chat_id: str, text: str, reply_to_message_id: int | None = None):
    tok = _token()
    url = API_BASE.format(token=tok) + "/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
