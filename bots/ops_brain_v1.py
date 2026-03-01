import subprocess, os, requests
from dotenv import load_dotenv
load_dotenv("env/telegram_daemon.env", override=True)

TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID="-5293321023"

def sh(cmd):
    return subprocess.getoutput(cmd)

def notify(msg):
    if not TOKEN: return
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":CHAT_ID,"text":msg}
    )

def check_poll():
    out=sh("launchctl list | grep jp.openclaw.tg_poll_loop")
    if not out or "\t-" in out:
        sh("launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.openclaw.tg_poll_loop.plist")
        notify("poll restarted")
        return
    notify("poll ok")

if __name__=="__main__":
    check_poll()
