import subprocess, sqlite3, os, requests, datetime

DB="data/openclaw.db"
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID="-5293321023"

def notify(msg):
    if TOKEN:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id":CHAT_ID,"text":msg}
        )

def run_apply(target):
    subprocess.call(["python","-m","bots.command_apply_v1",target])

def check_adopt():
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    cur.execute("""
        select target
        from decisions
        where decision='adopt'
        and updated_at >= datetime('now','-2 minutes')
    """)
    rows=cur.fetchall()
    for r in rows:
        target=r[0]
        notify(f"[AutoExecute] {target}")
        run_apply(target)
    conn.close()

if __name__=="__main__":
    check_adopt()
