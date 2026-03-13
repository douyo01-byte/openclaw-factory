from __future__ import annotations
import os
import sqlite3
import subprocess
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
ROOT = "/Users/doyopc/AI/openclaw-factory-daemon"
SLEEP = int(os.environ.get("SELF_STRENGTH_WATCHDOG_SLEEP", "180"))
QUIET_MIN = int(os.environ.get("SELF_STRENGTH_WATCHDOG_QUIET_MIN", "4"))
SEED_BURST = int(os.environ.get("SELF_STRENGTH_SEED_BURST", "2"))

def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    return con

def queue_state(con):
    return con.execute("""
    select
      count(*) as total,
      sum(case when coalesce(status,'')='approved' and coalesce(dev_stage,'')='execute_now' then 1 else 0 end) as execute_now,
      sum(case when coalesce(status,'')='approved' and coalesce(dev_stage,'')='pr_open' then 1 else 0 end) as pr_open
    from dev_proposals
    """).fetchone()

def last_event_age_min(con):
    row = con.execute("""
    select cast((julianday('now') - julianday(max(created_at))) * 1440 as integer)
    from ceo_hub_events
    """).fetchone()
    return int((row[0] if row and row[0] is not None else 999999))

def last_fallback_age_min(con):
    row = con.execute("""
    select cast((julianday('now') - julianday(max(created_at))) * 1440 as integer)
    from dev_proposals
    where coalesce(guard_reason,'')='mainstream_fallback'
    """).fetchone()
    return int((row[0] if row and row[0] is not None else 999999))

def seed_once():
    r = subprocess.run(
        ["python3", "bots/mainstream_fallback_supply_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(f"[self_strength_watchdog] seed rc={r.returncode}", flush=True)
    if (r.stdout or "").strip():
        print(r.stdout.strip(), flush=True)
    if (r.stderr or "").strip():
        print(r.stderr.strip(), flush=True)

def normalize_fallback_rows():
    con = connect()
    try:
        cur = con.execute("""
        update dev_proposals
        set project_decision='execute_now',
            dev_stage='execute_now'
        where coalesce(status,'')='approved'
          and coalesce(guard_reason,'') in ('mainstream_fallback','bootstrap_spec')
          and coalesce(project_decision,'')='execute_now'
          and coalesce(dev_stage,'')=''
        """)
        con.commit()
        print(f"[self_strength_watchdog] normalized={cur.rowcount}", flush=True)
    finally:
        con.close()

def main():
    while True:
        try:
            normalize_fallback_rows()
            con = connect()
            try:
                total, execute_now, pr_open = queue_state(con)
                quiet = last_event_age_min(con)
                fb_age = last_fallback_age_min(con)
            finally:
                con.close()

            execute_now = int(execute_now or 0)
            pr_open = int(pr_open or 0)

            print(
                f"[self_strength_watchdog] total={int(total or 0)} execute_now={execute_now} pr_open={pr_open} quiet_min={quiet} fallback_age_min={fb_age}",
                flush=True,
            )

            if execute_now == 0 and pr_open == 0:
                for _ in range(SEED_BURST):
                    seed_once()
                    time.sleep(8)
                normalize_fallback_rows()
            elif quiet >= QUIET_MIN and fb_age >= 10:
                for _ in range(SEED_BURST):
                    seed_once()
                    time.sleep(8)
                normalize_fallback_rows()
        except Exception as e:
            print(f"[self_strength_watchdog] error={e!r}", flush=True)

        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
