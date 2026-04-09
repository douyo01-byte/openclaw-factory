import os, sqlite3, time, requests

DB = os.environ.get("DB_PATH")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
SLEEP = 30

def send(msg):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT, "text": msg},
        timeout=20,
    )
    print(f"send_status={r.status_code}", flush=True)

def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("""
    create table if not exists telegram_report_log (
      task_id integer primary key,
      sent_at text default (datetime('now'))
    )
    """)

    r = cur.execute("""
    select id, task_text
    from router_tasks
    where target_bot='ops_exec'
      and status='done'
      and id not in (select task_id from telegram_report_log)
    order by id asc
    limit 1
    """).fetchone()

    if r:
        send(f"🚀 EXEC\n{r[1][:120]}")
        cur.execute("insert into telegram_report_log(task_id) values(?)", (r[0],))
        con.commit()
        print(f"reported_task={r[0]}", flush=True)
    else:
        print("nothing_to_report", flush=True)

    con.close()

while True:
    try:
        main()
    except Exception as e:
        print(f"telegram_report_v1 err={e!r}", flush=True)
    time.sleep(SLEEP)
