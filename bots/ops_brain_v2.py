import os, sqlite3, subprocess, requests

DB="data/openclaw.db"
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID="-5293321023"

def notify(msg):
    if TOKEN:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id":CHAT_ID,"text":msg}
        )

def run_apply():
    return subprocess.call(["python","-m","bots.command_apply_v1","--db",DB,"--limit","50"])

def mark_once(conn, k):
    cur=conn.execute("insert or ignore into executed_decisions(key) values(?)",(k,))
    return cur.rowcount==1

def main():
    conn=sqlite3.connect(DB)
    rows=conn.execute("""
      select target, updated_at
      from decisions
      where decision='adopt'
      order by updated_at asc
    """).fetchall()

    for target,ts in rows:
        k=f"adopt|{target}|{ts}"
        if not mark_once(conn,k):
            continue
        notify(f"[AutoExecute] {target}")
        rc=run_apply()
        notify(f"[Apply] rc={rc}")

    conn.commit()
    conn.close()

if __name__=="__main__":
    main()
