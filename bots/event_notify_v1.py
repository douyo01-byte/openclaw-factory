import os,time,sqlite3,requests

DB=os.environ["DB_PATH"]
TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
CHAT=os.environ["TELEGRAM_CHAT_ID"]

last_id=0

def tg(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":CHAT,"text":msg},
        timeout=20
    )

while True:
    conn=sqlite3.connect(DB)
    cur=conn.cursor()

    rows=cur.execute("""
    select id,event_type,proposal_id,title
    from ceo_hub_events
    where id>?
    and event_type in ('pr_created','merged','learning_result')
    order by id
    """,(last_id,)).fetchall()

    for r in rows:
        id_,t,p,title=r

        if t=="pr_created":
            tg(f"🚀 PR作成\nproposal #{p}\n{title}")

        elif t=="merged":
            tg(f"✅ merge\nproposal #{p}\n{title}")

        elif t=="learning_result":
            tg(f"🧠 learning\nproposal #{p}\n{title}")

        last_id=id_

    conn.close()
    time.sleep(5)
