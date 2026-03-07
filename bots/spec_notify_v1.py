import os,sqlite3,requests,time
DB=os.environ["DB_PATH"]
TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
CHAT=os.environ["TELEGRAM_CHAT_ID"]

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":CHAT,"text":msg},
        timeout=20
    ).raise_for_status()

def run():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    rows=conn.execute("""
    SELECT id,title,spec
    FROM dev_proposals
    WHERE spec_stage='refined'
      AND coalesce(notified_at,'')=''
    """).fetchall()
    print(f"rows={len(rows)}", flush=True)
    for r in rows:
        msg=f"🧠 Spec確認\nID:{r['id']}\n{r['title']}\n\n{r['spec']}"
        send(msg)
        conn.execute(
            "update dev_proposals set notified_at=datetime('now') where id=?",
            (r["id"],)
        )
        conn.commit()
        print(f"sent id={r['id']}", flush=True)

if __name__=="__main__":
    while True:
        run()
        time.sleep(20)
