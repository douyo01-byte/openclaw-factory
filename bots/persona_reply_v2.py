import os,requests,sqlite3,json

TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI=os.getenv("OPENAI_API_KEY")
CHAT_ID="-5293321023"
DB="data/openclaw.db"

def send(m):
    if TOKEN:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id":CHAT_ID,"text":m}
        )

def llm(text):
    if not OPENAI:
        return "APIキー未設定"
    r=requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization":f"Bearer {OPENAI}",
            "Content-Type":"application/json"
        },
        json={
            "model":"gpt-4o-mini",
            "messages":[
                {"role":"system","content":"あなたは有能で冷静なAI会社の共同創業者。端的だが人間らしく答える。"},
                {"role":"user","content":text}
            ]
        }
    )
    return r.json()["choices"][0]["message"]["content"]

def main():
    conn=sqlite3.connect(DB)
    rows=conn.execute(
        "select id,text from inbox_commands where status='new' order by id asc limit 20"
    ).fetchall()

    for i,text in rows:
        if text.lower().startswith("ok "):
            continue
        reply=llm(text)
        send(reply)
        conn.execute(
            "update inbox_commands set status='replied' where id=?",
            (i,)
        )

    conn.commit()
    conn.close()

if __name__=="__main__":
    main()
