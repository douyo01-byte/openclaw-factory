import sqlite3,time,os

DB=os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

while True:
    con=sqlite3.connect(DB)
    c=con.cursor()

    r=c.execute("""
    select count(*) from dev_proposals
    where coalesce(pr_status,'')='open'
    """).fetchone()[0]

    con.close()

    if r>3:
        print("PR STALL:",r)

    time.sleep(60)
