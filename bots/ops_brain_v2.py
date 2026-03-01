import subprocess, os, requests, sqlite3
from dotenv import load_dotenv
load_dotenv("env/telegram_daemon.env", override=True)

TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID="-5293321023"
DB_PATH=os.getenv("DB_PATH","data/openclaw.db")

def sh(cmd):
    return subprocess.getoutput(cmd)

def notify(msg):
    if not TOKEN: return
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg})

def check_poll():
    out=sh("launchctl list | grep jp.openclaw.tg_poll_loop")
    if not out or "\t-" in out:
        sh("launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.openclaw.tg_poll_loop.plist")
        notify("[OpsBrain] poll RESTARTED")
        return "restarted"
    return "ok"

def check_decisions():
    con=sqlite3.connect(DB_PATH)
    rows=con.execute("SELECT item_id,decision,target,'',updated_at FROM decisions WHERE updated_at > datetime('now','-10 minutes') ORDER BY item_id DESC").fetchall()
    con.close()
    return rows

def main():
    poll=check_poll()
    rows=check_decisions()
    if rows:
        for r in rows:
            notify(f"[Decision]\nid:{r[0]} {r[1]} {r[2]}\n理由:{r[3]}\n{r[4]}")

if __name__=="__main__":
    main()
