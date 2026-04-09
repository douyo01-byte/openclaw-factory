import os
import sqlite3
import subprocess
import time
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
PLIST = f"gui/{os.getuid()}/jp.openclaw.telegram_ops_executor_v1"
LOG = Path("/Users/doyopc/AI/openclaw-factory-daemon/logs/ops_exec_watchdog_v1.out")

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log(msg: str):
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def q():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def queue_counts():
    with q() as c:
        row = c.execute("""
            select
              sum(case when status='new' then 1 else 0 end) as new_cnt,
              sum(case when status='started' then 1 else 0 end) as started_cnt,
              sum(case when status='retry' then 1 else 0 end) as retry_cnt
            from router_tasks
            where target_bot='ops_exec'
        """).fetchone()
        return int(row["new_cnt"] or 0), int(row["started_cnt"] or 0), int(row["retry_cnt"] or 0)

def oldest_new_age_sec():
    with q() as c:
        row = c.execute("""
            select cast((julianday('now') - julianday(created_at)) * 86400 as integer) as age_sec
            from router_tasks
            where target_bot='ops_exec'
              and status='new'
            order by id asc
            limit 1
        """).fetchone()
        return int(row["age_sec"] or 0) if row else 0

def restart_executor():
    subprocess.run(["launchctl", "kickstart", "-k", PLIST], check=False)

def main():
    while True:
        try:
            new_cnt, started_cnt, retry_cnt = queue_counts()
            age_sec = oldest_new_age_sec()
            if new_cnt > 0 and age_sec >= 300:
                log(f"stuck_detected new={new_cnt} started={started_cnt} retry={retry_cnt} oldest_new_sec={age_sec} -> restart")
                restart_executor()
                time.sleep(15)
            else:
                log(f"ok new={new_cnt} started={started_cnt} retry={retry_cnt} oldest_new_sec={age_sec}")
        except Exception as e:
            log(f"watchdog_err={e!r}")
        time.sleep(60)

if __name__ == "__main__":
    main()
