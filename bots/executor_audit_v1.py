import os
import sqlite3
import time

DB=os.environ.get("OCLAW_DB_PATH")

def log(msg):
    print(msg, flush=True)

def main():
    conn=sqlite3.connect(DB)
    while True:
        try:
            approved=conn.execute("""
            select count(*) from dev_proposals
            where status='approved'
            and project_decision='execute_now'
            and guard_status='safe'
            """).fetchone()[0]

            open_pr=conn.execute("""
            select count(*) from dev_proposals
            where pr_status='open'
            """).fetchone()[0]

            merged=conn.execute("""
            select count(*) from dev_proposals
            where status='merged'
            """).fetchone()[0]

            log(f"[executor_audit] approved_queue={approved} open_pr={open_pr} merged={merged}")

            if approved>0 and open_pr==0:
                log("[executor_audit] warning executor stall possible")

        except Exception as e:
            log(f"[executor_audit] error {e}")

        time.sleep(120)

if __name__=="__main__":
    main()
