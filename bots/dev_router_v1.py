import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def route_once():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("pragma busy_timeout=30000")

    con.execute("""
    update dev_proposals
    set project_decision='execute_now'
    where status='approved'
      and coalesce(project_decision,'')=''
    """)

    con.execute("""
    update dev_proposals
    set dev_stage='execute_now'
    where status='approved'
      and coalesce(project_decision,'')='execute_now'
      and coalesce(spec_stage,'')='decomposed'
      and coalesce(dev_stage,'')=''
    """)

    con.commit()
    con.close()

def main():
    while True:
        try:
            route_once()
        except Exception as e:
            print(repr(e), flush=True)
        time.sleep(5)

if __name__ == "__main__":
    main()
