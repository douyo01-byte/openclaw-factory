import subprocess, sqlite3, os, sys, time

def sh(cmd):
    return subprocess.getoutput(cmd)

def check_poll():
    out = sh("launchctl list | grep jp.openclaw.tg_poll_loop")
    if not out or "\t-" in out:
        sh("launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.openclaw.tg_poll_loop.plist")
        return "restarted"
    return "ok"

def main():
    status = check_poll()
    print("poll:", status)

if __name__=="__main__":
    main()
