import os, requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
r = requests.get(url, timeout=30)
r.raise_for_status()

data = r.json()
results = data.get("result", [])

if not results:
    print("No updates yet.")
    print("1) Open your bot in Telegram")
    print("2) Press Start (/start) or send any message")
    print("3) Run this script again")
    raise SystemExit(0)

# 最新のメッセージからchat_idを探す
for u in reversed(results):
    msg = u.get("message") or u.get("channel_post") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    title = chat.get("title") or ""
    username = chat.get("username") or ""
    if chat_id is not None:
        print("Found chat:")
        print(" chat_id:", chat_id)
        print(" type:", chat_type)
        if title: print(" title:", title)
        if username: print(" username:", username)
        break
else:
    print("No chat_id found in updates. Send a normal message to the bot and retry.")
