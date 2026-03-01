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

def run_apply(target):
    subprocess.call(["python","-m","bots.command_apply_v1",target])

def get_kv(conn,k,default=""):
    r=conn.execute("select v from kv where k=?",(k,)).fetchone()
    return r[0] if r else default

def set_kv(conn,k,v):
    conn.execute("insert into kv(k,v) values(?,?) on conflict(k) do update set v=excluded.v",(k,v))

def main():
    conn=sqlite3.connect(DB)
    last=get_kv(conn,"ops_last_decision_ts","1970-01-01 00:00:00")

    rows=conn.execute("""
      select target, updated_at
      from decisions
      where decision='adopt'
        and updated_at > ?
      order by updated_at asc
    """,(last,)).fetchall()

    max_ts=last
    for target,ts in rows:
        notify(f"[AutoExecute] {target}")
        run_apply(target)
        if ts>max_ts: max_ts=ts

    if max_ts!=last:
        set_kv(conn,"ops_last_decision_ts",max_ts)
        conn.commit()
    conn.close()

if __name__=="__main__":
    main()
