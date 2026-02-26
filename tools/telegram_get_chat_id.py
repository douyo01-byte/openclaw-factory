import os, requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
assert token, "TELEGRAM_BOT_TOKEN is missing in .env"

url = f"https://api.telegram.org/bot{token}/getUpdates"
r = requests.get(url, timeout=30)
r.raise_for_status()
data = r.json()

print("=== recent updates ===")
for u in data.get("result", [])[-10:]:
    msg = u.get("message") or u.get("channel_post") or {}
    chat = msg.get("chat", {})
    text = msg.get("text", "")
    print("chat_id:", chat.get("id"), "title:", chat.get("title"), "user:", chat.get("username"), "text:", text)
