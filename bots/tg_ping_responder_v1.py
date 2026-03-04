import os,sqlite3,time,urllib.request,urllib.parse,json
DB_PATH=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "data/openclaw.db"
TOKEN=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
BASE=f"https://api.telegram.org/bot{TOKEN}"
def tg_send(chat_id,text,reply_to=None):
    if not TOKEN:
        return False
    payload={"chat_id":chat_id,"text":text}
    if reply_to:
        payload["reply_to_message_id"]=reply_to
    data=urllib.parse.urlencode(payload).encode()
    req=urllib.request.Request(f"{BASE}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out=r.read().decode("utf-8","replace")
        return '"ok":true' in out
    except Exception:
        return False
def main():
    conn=sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("pragma journal_mode=WAL;")
    conn.execute("pragma synchronous=NORMAL;")
    conn.execute("pragma busy_timeout=8000;")
    conn.execute("pragma busy_timeout=8000;")
    rows=conn.execute("select id,chat_id,message_id,trim(text) as t from inbox_commands where processed=0 and trim(text) like '/ping%' order by id asc limit 20").fetchall()
    n=0
    for rid,chat_id,mid,t in rows:
        ok=tg_send(chat_id,"pong",mid)
        conn.execute("update inbox_commands set status=?, processed=1, applied_at=datetime('now') where id=?", ("applied" if ok else "error", rid))
        n+=1
        time.sleep(0.2)
    conn.commit()
    conn.close()

if __name__=="__main__":
    main()
