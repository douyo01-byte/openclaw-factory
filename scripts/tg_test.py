import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN missing in .env")
    exit()

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID missing in .env")
    exit()

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

payload = {
    "chat_id": CHAT_ID,
    "text": "🚀 OpenClaw Factory\nTelegram送信テスト成功！"
}

res = requests.post(url, json=payload)

print("Status:", res.status_code)
print("Response:", res.text)
