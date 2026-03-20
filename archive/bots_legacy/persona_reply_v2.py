import os
import sqlite3
import requests

DB = "data/openclaw.db"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
CHAT_ID = "-5293321023"


def send(msg):
    if not TOKEN:
        return
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg},
    )


def llm(text):
    if not OPENAI_KEY:
        return "OPENAI_API_KEY が設定されていません"

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "あなたは有能で冷静なAI会社の共同創業者。端的だが人間らしく答える。",
                },
                {"role": "user", "content": text},
            ],
        },
    )

    try:
        data = r.json()
    except Exception:
        return "LLMレスポンス解析失敗"

    if "choices" not in data:
        return f"LLM_ERROR: {data}"

    return data["choices"][0]["message"]["content"]


def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "select id,text from inbox_commands where status='new' order by id asc limit 20"
    ).fetchall()

    for i, text in rows:
        if text.lower().startswith("ok "):
            continue

        reply = llm(text)
        send(reply)

        conn.execute("update inbox_commands set status='replied' where id=?", (i,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
