import os,sqlite3,time,urllib.parse,urllib.request
DB=os.environ.get("DB_PATH","data/openclaw.db")
TOK=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
def send(chat_id,text,reply_to=None):
    if not TOK:
        return
    url=f"https://api.telegram.org/bot{TOK}/sendMessage"
    payload={"chat_id":chat_id,"text":text}
    if reply_to:
        payload["reply_to_message_id"]=reply_to
    data=urllib.parse.urlencode(payload).encode()
    with urllib.request.urlopen(url,data=data,timeout=20) as r:
        r.read()
def tick(conn):
    rows=conn.execute(
        "select id,chat_id,message_id from inbox_commands where processed=0 and trim(text) like '/ping%' order by id asc limit 50"
    ).fetchall()
    for rid,chat_id,mid in rows:
        send(chat_id,"pong",mid)
        conn.execute("update inbox_commands set status='applied', processed=1 where id=?", (rid,))
    return len(rows)
def main():
    while True:
        conn=sqlite3.connect(DB,timeout=30)
        conn.execute("pragma journal_mode=WAL;")
        n=tick(conn)
        conn.commit()
        conn.close()

        time.sleep(2)
if __name__=="__main__":
    main()
