import os,time,requests,sqlite3

TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
API=f"https://api.telegram.org/bot{TOKEN}/getUpdates"

DB=os.environ["DB_PATH"]

def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

offset=0

while True:
    try:
        r=requests.get(API,params={"offset":offset+1,"timeout":30}).json()
        for u in r.get("result",[]):
            offset=u["update_id"]
            m=u.get("message")
            if not m: 
                continue
            text=m.get("text","")
            chat=m["chat"]["id"]
            mid=m["message_id"]
            with conn() as c:
                c.execute(
                "insert into tg_private_chat_log(message_id,chat_id,text) values(?,?,?)",
                (mid,chat,text))
    except:
        pass
    time.sleep(2)
