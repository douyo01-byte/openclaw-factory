import os,time,requests,sqlite3

TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
API=f"https://api.telegram.org/bot{TOKEN}/getUpdates"
DB=os.environ["DB_PATH"]

print(f"[ingest_private] boot db={DB} token_head={TOKEN[:12]}...", flush=True)

def conn():
    c=sqlite3.connect(DB, timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    return c

offset=0

while True:
    try:
        r=requests.get(API, params={"offset": offset+1, "timeout": 30}, timeout=35)
        r.raise_for_status()
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

            print(
                f"[ingest_private] update_id={offset} chat_id={chat_id} chat_type={chat_type} mid={mid} text_head={text[:80]!r}",
                flush=True
            )

            if chat_type != "private":
                continue

            with conn() as c:
                c.execute(
                    "insert or ignore into tg_private_chat_log(message_id,chat_id,text,router_ingested,created_at) values(?,?,?,'',datetime('now'))",
                    (mid,chat_id,text)
                )
                c.commit()

            print(f"[ingest_private] inserted mid={mid} chat_id={chat_id}", flush=True)

    except Exception as e:
        print(f"[ingest_private] err={e!r}", flush=True)
        time.sleep(2)
