import os
import requests
import sqlite3

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = "-5293321023"
DB = "data/openclaw.db"


def send(m):
    if TOKEN:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": m},
        )


def reply_logic(text):
    t = text.lower()
    if t.startswith("ok "):
        return None
    if "提案" in text:
        return "提案ありがとうございます。内容を整理し判断に回します。"
    if "どう思う" in text:
        return "現状データを基に分析します。少し待ってください。"
    if "やぁ" in text or "こんにちは" in text:
        return "お疲れ様です。現在システムは正常稼働中です。"
    return "内容を受領しました。必要に応じて処理します。"


def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "select id,text from inbox_commands where status='new' order by id asc limit 20"
    ).fetchall()
    for i, text in rows:
        r = reply_logic(text)
        if r:
            send(r)
        conn.execute("update inbox_commands set status='replied' where id=?", (i,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
