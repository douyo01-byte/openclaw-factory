import os,time,requests,sqlite3

TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
API=f"https://api.telegram.org/bot{TOKEN}/getUpdates"
DB=os.environ["DB_PATH"]

print(f"[ingest_private] boot db={DB} token_head={TOKEN[:12]}...", flush=True)

def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

offset=0

while True:
    try:
        r=requests.get(API, params={"offset": offset+1, "timeout": 30}, timeout=35)
        data=r.json()
        rows=data.get("result",[])
        print(f"[ingest_private] polled count={len(rows)} offset={offset}", flush=True)
        for u in rows:
            offset=u["update_id"]
            m=u.get("message")
            if not m:
                continue
            chat=m.get("chat", {})
            text=m.get("text","")
            mid=m.get("message_id")
            chat_id=chat.get("id")
            chat_type=chat.get("type","")
            with conn() as c:
                c.execute(
                    "insert into tg_private_chat_log(message_id,chat_id,text) values(?,?,?)",
                    (mid,chat_id,text)
                )
                c.commit()
    except Exception as e:
    time.sleep(2)
